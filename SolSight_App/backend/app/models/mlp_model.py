"""
MLP health-classification model.

Input: concatenation of
  - CNN image features (feature_dim from DefectCNN, default 128)
  - Operational/numeric features: voltage, current, power, temperature,
    efficiency, defect_confidence, historical_health_avg  (7 values)

Output: 3-way softmax over Healthy / Warning / Critical.
"""
import torch
import torch.nn as nn

HEALTH_CLASSES = ["Healthy", "Warning", "Critical"]


class HealthMLP(nn.Module):
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
        # Health score: weighted combination that rewards "Healthy" probability
        health_score = float(probs[0] * 100 + probs[1] * 55 + probs[2] * 15)
        return HEALTH_CLASSES[idx], round(health_score, 1), prob_dict