"""
Orchestrates the full SolSight inference pipeline:

  Image + Operational Data
        │
        ▼
  CNN  ──► defect label, confidence, 128-d feature vector
        │
        ▼
  MLP  ──► Healthy / Warning / Critical + health_score
        │
        ▼
  Bi-LSTM (uses this panel's historical health_scores) ──► 30/60/90 day forecast
        │
        ▼
  Maintenance recommendation (status + defect + forecast)

Each stage only uses its network if trained weights were found in
saved_models/. Otherwise it falls back to the physics/rule-based logic in
diagnostics.py, and the response says which path was taken
(`analysis_mode`) so nobody mistakes an estimate for a model output.
"""
import io
import logging
import os
from datetime import datetime
from typing import List, Optional, Tuple

import torch
from PIL import Image, UnidentifiedImageError
from torchvision import transforms

from app.models.cnn_model import DefectCNN, IMAGE_SIZE
from app.models.mlp_model import HealthMLP
from app.models.bilstm_model import DegradationBiLSTM, FORECAST_HORIZONS_DAYS
from app.services import diagnostics as dx

log = logging.getLogger("solsight.prediction")

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "saved_models")

_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


class InvalidImageError(ValueError):
    pass


class PredictionService:
    """Loads all three models once and exposes a single `.run_inspection()` call."""

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.cnn = DefectCNN(pretrained=False).to(self.device)
        self.mlp = HealthMLP().to(self.device)
        self.bilstm = DegradationBiLSTM().to(self.device)
        self.trained = {
            "cnn": self._load("cnn_best.pt", self.cnn),
            "mlp": self._load("mlp_best.pt", self.mlp),
            "bilstm": self._load("bilstm_best.pt", self.bilstm),
        }
        self.cnn.eval()
        self.mlp.eval()
        self.bilstm.eval()

    def _load(self, name: str, model: torch.nn.Module) -> bool:
        path = os.path.join(MODEL_DIR, name)
        if not (os.path.exists(path) and os.path.getsize(path) > 0):
            log.warning("%s not found or empty; using rule-based fallback for this stage", name)
            return False
        try:
            state = torch.load(path, map_location=self.device, weights_only=True)
            model.load_state_dict(state)
            log.info("loaded %s", name)
            return True
        except Exception as e:
            log.warning("could not load %s (%s); using rule-based fallback", name, e)
            return False

    @staticmethod
    def _decode_image(image_bytes: bytes) -> Image.Image:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.load()
            return img.convert("RGB")
        except (UnidentifiedImageError, OSError) as e:
            raise InvalidImageError("Uploaded file is not a readable image") from e

    def _numeric_feature_vector(self, voltage, current, temperature, rated_power,
                                defect_confidence, historical_avg_health) -> torch.Tensor:
        power = voltage * current
        efficiency = (power / rated_power) if rated_power else 0.0
        vals = [voltage, current, power, temperature, efficiency, defect_confidence, historical_avg_health]
        return torch.tensor(vals, dtype=torch.float32, device=self.device)

    def run_inspection(
        self,
        image_bytes: Optional[bytes],
        voltage: float,
        current: float,
        temperature: float,
        rated_power: float,
        history: List[Tuple[datetime, float]],
    ) -> dict:
        img = self._decode_image(image_bytes) if image_bytes else None
        power_output = voltage * current
        pr = dx.performance_ratio(power_output, rated_power, temperature)
        past_scores = [s for _, s in history]
        mode = {}

        # --- 1. Defect detection ---
        cnn_features = None
        if img is not None and (self.trained["cnn"] or self.trained["mlp"]):
            x = _transform(img).unsqueeze(0).to(self.device)
            cnn_label, cnn_conf, cnn_probs, cnn_features = self.cnn.predict(x)
        if img is not None and self.trained["cnn"]:
            defect_label, defect_conf, defect_probs = cnn_label, cnn_conf, cnn_probs
            mode["defect"] = "cnn"
        else:
            hot = dx.image_hotspot_score(img) if img is not None else 0.0
            defect_label, defect_conf, defect_probs = dx.estimate_defect(pr, temperature, hot)
            mode["defect"] = "rule-based"

        # --- 2. Health classification ---
        if self.trained["mlp"] and cnn_features is not None:
            historical_avg = sum(past_scores) / len(past_scores) if past_scores else 90.0
            numeric = self._numeric_feature_vector(
                voltage, current, temperature, rated_power, defect_conf, historical_avg
            )
            status, health, health_probs = self.mlp.predict(cnn_features, numeric)
            mode["health"] = "mlp"
        else:
            health = dx.health_score(pr, temperature, defect_label, defect_conf)
            status = dx.status_for(health)
            health_probs = dx.status_probabilities(health)
            mode["health"] = "rule-based"

        # --- 3. Degradation forecast ---
        if self.trained["bilstm"] and len(past_scores) >= 2:
            preds = self.bilstm.predict(past_scores + [health])
            mode["forecast"] = "bilstm"
        else:
            preds = dx.trend_forecast(history + [(datetime.utcnow(), health)], health,
                                      FORECAST_HORIZONS_DAYS)
            mode["forecast"] = "trend"
        forecast = [{"day": d, "predicted_health": p} for d, p in zip(FORECAST_HORIZONS_DAYS, preds)]

        # --- 4. Power + recommendation ---
        recommendation = dx.build_recommendation(status, defect_label, health, forecast)

        return {
            "detected_defect": defect_label,
            "confidence": round(defect_conf * 100, 1),
            "defect_probabilities": {k: round(v * 100, 1) for k, v in defect_probs.items()},
            "status": status,
            "health_score": health,
            "health_probabilities": {k: round(v * 100, 1) for k, v in health_probs.items()},
            "power_output": round(power_output, 2),
            "expected_power": round(dx.expected_power(rated_power, temperature), 1),
            "performance_ratio": round(pr, 3),
            "power_loss_pct": dx.power_loss_pct(power_output, rated_power, temperature),
            "degradation_forecast": forecast,
            "recommendation": recommendation,
            "analysis_mode": mode,
        }


# Singleton instance used by the routers
prediction_service = PredictionService()
