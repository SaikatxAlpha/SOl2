"""
Physics / rule-based panel diagnostics.

Used in two ways:
  1. As the fallback when a model's trained weights aren't present in
     saved_models/ -- an untrained network gives random output, so we'd
     rather give a reasoned estimate and say so.
  2. As the source of the electrical numbers (expected power, performance
     ratio, thermal stress) that feed the health score either way.

Assumptions (document these in any report built on the output):
  - Readings are taken near peak sun, so rated (STC) power is a fair
    baseline. We have no irradiance sensor.
  - Crystalline-silicon temperature coefficient of -0.40 %/°C above 25 °C.
  - Normal ageing of ~0.7 %/year when there isn't enough history to fit
    a trend.
"""
from datetime import datetime
from math import exp
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageStat

TEMP_COEFF_PER_C = -0.004
STC_TEMP_C = 25.0
THERMAL_STRESS_C = 65.0
BASELINE_DECLINE_PER_DAY = 0.7 / 365  # health points per day

HEALTHY_MIN = 75.0
WARNING_MIN = 50.0

DEFECT_CLASSES = ["Normal", "Crack", "Hotspot", "Soiling"]


# ---------- electrical ----------
def expected_power(rated_power: float, temperature: float) -> float:
    """Rated output adjusted for cell temperature."""
    factor = 1 + TEMP_COEFF_PER_C * (temperature - STC_TEMP_C)
    return max(rated_power * factor, 0.0)


def performance_ratio(power_output: float, rated_power: float, temperature: float) -> float:
    exp_p = expected_power(rated_power, temperature)
    if exp_p <= 0:
        return 0.0
    return max(0.0, min(power_output / exp_p, 1.15))


def power_loss_pct(power_output: float, rated_power: float, temperature: float) -> float:
    """Loss against the temperature-corrected expectation, not raw nameplate."""
    exp_p = expected_power(rated_power, temperature)
    if exp_p <= 0:
        return 0.0
    return round(max(0.0, (1 - power_output / exp_p) * 100), 1)


# ---------- image ----------
def image_hotspot_score(img: Image.Image) -> float:
    """
    0..1 score for a localized bright region, which is what a hotspot looks
    like on a thermal image. Works on the luminance channel so it doesn't
    care about the camera's colour palette. Visual (non-thermal) photos
    with glare can trigger it too, so it's only ever used as a nudge.
    """
    gray = img.convert("L").resize((128, 128))
    stat = ImageStat.Stat(gray)
    mean, std = stat.mean[0], stat.stddev[0]
    if std < 1:
        return 0.0
    threshold = mean + 2.5 * std
    pixels = gray.getdata()
    hot = sum(1 for p in pixels if p > threshold) / len(pixels)
    # A real hotspot is a small fraction of the panel: 0.3% - 8% of pixels.
    if hot < 0.003 or hot > 0.08:
        return 0.0
    peak = max(pixels)
    contrast = (peak - mean) / 255
    return max(0.0, min(1.0, contrast * 1.6))


# ---------- defect ----------
def _softmax(scores: Dict[str, float]) -> Dict[str, float]:
    m = max(scores.values())
    e = {k: exp(v - m) for k, v in scores.items()}
    total = sum(e.values())
    return {k: v / total for k, v in e.items()}


def estimate_defect(pr: float, temperature: float, hotspot_score: float = 0.0
                    ) -> Tuple[str, float, Dict[str, float]]:
    """
    Infer the most likely defect from electrical + thermal evidence.
    Each class gets a score; softmax turns them into probabilities.
      - Normal:  output close to expected, cell temperature reasonable
      - Soiling: moderate, uniform loss (dust/bird droppings)
      - Crack:   heavy loss -- typical of a bypassed substring
      - Hotspot: loss together with high temperature or a thermal hot region
    """
    loss = max(0.0, 1 - pr)
    heat = max(0.0, (temperature - 50) / 25)  # 0 at 50°C, 1 at 75°C

    scores = {
        "Normal": 4.0 * (0.12 - loss) * 10 - heat * 2,
        "Soiling": 3.0 - abs(loss - 0.18) * 25 - heat,
        # one-sided: losing more than a substring's worth is still crack-like
        "Crack": 3.0 - max(0.38 - loss, 0) * 14 - max(loss - 0.38, 0) * 3 - heat * 0.5,
        "Hotspot": heat * 3.5 + hotspot_score * 4 + loss * 4 - 1.8,
    }
    probs = _softmax(scores)
    label = max(probs, key=probs.get)
    return label, probs[label], probs


# ---------- health ----------
def health_score(pr: float, temperature: float, defect: str, defect_conf: float) -> float:
    score = min(pr, 1.0) * 100
    if temperature > THERMAL_STRESS_C:
        score -= (temperature - THERMAL_STRESS_C) * 0.8
    defect_penalty = {"Normal": 0, "Soiling": 4, "Hotspot": 10, "Crack": 12}.get(defect, 0)
    score -= defect_penalty * defect_conf
    return round(max(0.0, min(100.0, score)), 1)


def status_for(score: float) -> str:
    if score >= HEALTHY_MIN:
        return "Healthy"
    if score >= WARNING_MIN:
        return "Warning"
    return "Critical"


def status_probabilities(score: float) -> Dict[str, float]:
    """Soft version of status_for, so the UI has something to show per class."""
    return _softmax({
        "Healthy": (score - HEALTHY_MIN) / 6,
        "Warning": -abs(score - (HEALTHY_MIN + WARNING_MIN) / 2) / 8 + 1,
        "Critical": (WARNING_MIN - score) / 6,
    })


# ---------- forecast ----------
STEP_DROP = 15.0  # points lost between two inspections that count as an event


def _since_last_step(history: Sequence[Tuple[datetime, float]]) -> Sequence[Tuple[datetime, float]]:
    """
    A sudden drop (hail, a cracked cell, a failed diode) is an event, not a
    trend. Fitting a line across it would forecast the panel to zero, so
    only the inspections after the most recent step are used.
    """
    for k in range(len(history) - 1, 0, -1):
        if history[k - 1][1] - history[k][1] >= STEP_DROP:
            return history[k:]
    return history


def decline_per_day(history: Sequence[Tuple[datetime, float]]) -> float:
    """
    Least-squares slope of health vs. time, in points lost per day.
    Falls back to normal ageing when there's too little data or the fit
    says the panel is improving (cleaning, sensor noise).
    """
    history = _since_last_step(history)
    if len(history) < 3:
        return BASELINE_DECLINE_PER_DAY
    t0 = history[0][0]
    xs = [(t - t0).total_seconds() / 86400 for t, _ in history]
    ys = [s for _, s in history]
    span = xs[-1] - xs[0]
    if span < 7:
        return BASELINE_DECLINE_PER_DAY
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    var = sum((x - mx) ** 2 for x in xs)
    if var == 0:
        return BASELINE_DECLINE_PER_DAY
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var
    return max(-slope, BASELINE_DECLINE_PER_DAY)


def trend_forecast(history: Sequence[Tuple[datetime, float]], current: float,
                   horizons: List[int]) -> List[float]:
    rate = decline_per_day(history)
    return [round(max(0.0, current - rate * d), 1) for d in horizons]


# ---------- recommendation ----------
_DEFECT_ACTION = {
    "Soiling": "Clean the module surface; re-measure after cleaning to confirm the loss recovers.",
    "Hotspot": "Check bypass diodes and look for shading or a failing cell with a thermal camera.",
    "Crack": "Inspect for micro-cracks (EL imaging if available) and plan module replacement.",
    "Normal": "",
}


def build_recommendation(status: str, defect: str, current: float,
                         forecast: List[dict]) -> str:
    action = _DEFECT_ACTION.get(defect, "")
    end = forecast[-1] if forecast else None

    if status == "Critical":
        base = f"Critical condition ({defect.lower()}). Take the panel out of service for on-site inspection."
    elif status == "Warning":
        base = f"Early signs of {defect.lower()}." if defect != "Normal" else "Output is below expected."
        crossing = next((p for p in forecast if p["predicted_health"] < WARNING_MIN), None)
        if crossing:
            base += f" At the current rate it reaches Critical within {crossing['day']} days, so act this cycle."
        else:
            base += " Schedule an inspection in the next maintenance window."
    else:
        if defect != "Normal":
            base = f"Healthy for now, but readings point to early {defect.lower()}. {action}"
        else:
            base = "Operating normally. Keep the standard maintenance schedule."
        if end and end["predicted_health"] < HEALTHY_MIN:
            base += f" At the current rate it reaches {end['predicted_health']}% in {end['day']} days."
        return base.strip()

    return f"{base} {action}".strip()
