"""
Module 4 — Bi-LSTM Degradation Trend Model
==========================================
Bi-LSTM degradation-prediction model.

Takes a sequence of past health scores (0-100) for a panel and forecasts
future health at fixed horizons (30 / 60 / 90 days by default).

The network is trained to output the *fractional decline* from the last
observed score at each horizon, i.e. (current - future) / 100. Keeping
train and inference on the same target is what makes the saved weights
usable -- see Module4/Training/train_bilstm.py.
"""
from typing import List
import torch
import torch.nn as nn

FORECAST_HORIZONS_DAYS = [30, 60, 90]


class DegradationBiLSTM(nn.Module):
    def __init__(self, input_dim: int = 1, hidden_dim: int = 32, num_layers: int = 2,
                 num_horizons: int = len(FORECAST_HORIZONS_DAYS)):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=0.2 if num_layers > 1 else 0.0,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_dim * 2, 32),
            nn.ReLU(),
            nn.Linear(32, num_horizons),
        )

    def forward(self, x):
        # x: (B, T, 1), scores scaled to 0-1
        out, _ = self.lstm(x)
        last_step = out[:, -1, :]  # (B, hidden_dim*2)
        return self.head(last_step)  # (B, num_horizons) fractional decline per horizon

    @torch.no_grad()
    def predict(self, history: List[float]) -> List[float]:
        """
        history: past health scores, oldest first (e.g. [96, 94, 91, 87, 81])
        Returns the predicted health score at each horizon in FORECAST_HORIZONS_DAYS.
        """
        self.eval()
        if not history:
            return []
        x = torch.tensor(history, dtype=torch.float32).view(1, -1, 1) / 100.0
        declines = self.forward(x)[0]
        current = history[-1]
        preds = []
        last = current
        for d in declines.tolist():
            # Health doesn't recover on its own, so keep the curve non-increasing.
            value = min(last, current - max(d, 0.0) * 100)
            value = max(0.0, min(100.0, value))
            preds.append(round(value, 1))
            last = value
        return preds
