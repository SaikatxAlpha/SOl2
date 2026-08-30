"""
Module 1 — MLP Model Architecture
==================================
Classifies panel condition as Healthy / Warning / Critical using
extracted features (CNN image features + operational readings).

This file defines ONLY the model. Training logic lives in
Module2/Training/train_health_mlp.py, which imports this class.
"""
import torch
import torch.nn as nn

HEALTH_CLASSES = ["Healthy", "Warning", "Critical"]


class HealthMLP(nn.Module):
    """
    Input = concatenation of:
      - cnn_feature_dim (default 128) image features extracted upstream
      - numeric_feature_dim (default 7): voltage, current, power,
        temperature, efficiency, defect_confidence, historical_health_avg

    Output = 3-way softmax over HEALTH_CLASSES.
    """

    def __init__(self, cnn_feature_dim: int = 128, numeric_feature_dim: int = 7, num_classes: int = 3):
        super().__init__()
        input_dim = cnn_feature_dim + numeric_feature_dim
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.4),

            nn.Linear(256, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(64, num_classes),
        )

    def forward(self, x):
        return self.net(x)

    @torch.no_grad()
    def predict(self, cnn_features: torch.Tensor, numeric_features: torch.Tensor):
        """
        cnn_features: (feature_dim,) tensor
        numeric_features: (numeric_feature_dim,) tensor
        Returns (status_label, health_score_0_100, prob_dict)
        """
        self.eval()
        x = torch.cat([cnn_features, numeric_features], dim=0).unsqueeze(0)
        logits = self.forward(x)
        probs = torch.softmax(logits, dim=1)[0]
        idx = int(torch.argmax(probs).item())
        prob_dict = {cls: float(probs[i]) for i, cls in enumerate(HEALTH_CLASSES)}
        health_score = float(probs[0] * 100 + probs[1] * 55 + probs[2] * 15)
        return HEALTH_CLASSES[idx], round(health_score, 1), prob_dict
