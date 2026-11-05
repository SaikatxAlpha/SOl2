from datetime import datetime, timedelta

from app.services import diagnostics as dx


def run(v, i, t, rated=400.0, hot=0.0):
    pr = dx.performance_ratio(v * i, rated, t)
    defect, conf, _ = dx.estimate_defect(pr, t, hot)
    score = dx.health_score(pr, t, defect, conf)
    return defect, score, dx.status_for(score)


def test_expected_power_drops_with_heat():
    assert dx.expected_power(400, 25) == 400
    assert round(dx.expected_power(400, 50), 1) == 360.0


def test_good_reading_is_healthy():
    defect, score, status = run(33.0, 10.8, 45)
    assert defect == "Normal"
    assert status == "Healthy"


def test_moderate_uniform_loss_reads_as_soiling():
    defect, score, status = run(32.0, 10.0, 40)  # ~15% below expected
    assert defect == "Soiling"
    assert status in ("Healthy", "Warning")


def test_heavy_loss_reads_as_crack_and_not_healthy():
    defect, score, status = run(24.0, 8.0, 40)
    assert defect == "Crack"
    assert status != "Healthy"


def test_large_loss_on_cool_panel_is_still_crack():
    defect, _, status = run(16.0, 8.0, 30)
    assert defect == "Crack"
    assert status == "Critical"


def test_hot_and_underperforming_reads_as_hotspot():
    defect, score, status = run(29.0, 8.0, 74)
    assert defect == "Hotspot"
    assert status != "Healthy"


def test_thermal_image_nudges_towards_hotspot():
    pr = dx.performance_ratio(31.0 * 9.0, 400, 55)
    _, _, without = dx.estimate_defect(pr, 55, 0.0)
    _, _, with_hot = dx.estimate_defect(pr, 55, 0.9)
    assert with_hot["Hotspot"] > without["Hotspot"]


def test_probabilities_sum_to_one():
    _, _, probs = dx.estimate_defect(0.8, 50)
    assert abs(sum(probs.values()) - 1) < 1e-9
    assert set(probs) == set(dx.DEFECT_CLASSES)


def test_forecast_uses_observed_trend():
    start = datetime(2026, 1, 1)
    history = [(start + timedelta(days=7 * k), 95 - 2 * k) for k in range(6)]
    rate = dx.decline_per_day(history)
    assert abs(rate - 2 / 7) < 1e-6
    preds = dx.trend_forecast(history, history[-1][1], [30, 60, 90])
    assert preds == sorted(preds, reverse=True)
    assert preds[0] < history[-1][1]


def test_sudden_drop_is_not_extrapolated_as_a_trend():
    start = datetime(2026, 1, 1)
    scores = [97, 97, 98, 97, 96, 55, 54, 52, 51]
    history = [(start + timedelta(days=7 * k), s) for k, s in enumerate(scores)]
    rate = dx.decline_per_day(history)
    # ~1.3 pts/week after the event, not the ~6 pts/week a full-range fit gives
    assert rate < 0.25
    assert dx.trend_forecast(history, 51, [90])[0] > 25


def test_forecast_never_predicts_recovery():
    start = datetime(2026, 1, 1)
    improving = [(start + timedelta(days=10 * k), 60 + 5 * k) for k in range(5)]
    assert dx.decline_per_day(improving) == dx.BASELINE_DECLINE_PER_DAY
