"""
CNN defect-detection model.

Architecture: a lightweight CNN head bolted onto a torchvision ResNet18
backbone (pretrained on ImageNet). Only the head is trained on the solar
panel dataset, which keeps training fast and works well on a small dataset.

Classes: Normal, Crack, Hotspot, Soiling
"""
import torch
import torch.nn as nn
from torchvision import models

DEFECT_CLASSES = ["Normal", "Crack", "Hotspot", "Soiling"]


class DefectCNN(nn.Module):
    def __init__(self, num_classes: int = len(DEFECT_CLASSES), pretrained: bool = True, feature_dim: int = 128):
        super().__init__()
        backbone = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1 if pretrained else None)
        # Strip the final FC layer, keep everything else as a feature extractor
        self.backbone = nn.Sequential(*list(backbone.children())[:-1])  # -> (B, 512, 1, 1)
        self.feature_head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(512, feature_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
        )
        self.classifier = nn.Linear(feature_dim, num_classes)

    def forward(self, x, return_features: bool = False):
        x = self.backbone(x)
        feats = self.feature_head(x)
        logits = self.classifier(feats)
        if return_features:
            return logits, feats
        return logits

    @torch.no_grad()
    def predict(self, x):
        """Returns (predicted_label, confidence, prob_dict, feature_vector)."""
        self.eval()
        logits, feats = self.forward(x, return_features=True)
        probs = torch.softmax(logits, dim=1)[0]
        idx = int(torch.argmax(probs).item())
        prob_dict = {cls: float(probs[i]) for i, cls in enumerate(DEFECT_CLASSES)}
        return DEFECT_CLASSES[idx], float(probs[idx]), prob_dict, feats[0]


IMAGE_SIZE = 224