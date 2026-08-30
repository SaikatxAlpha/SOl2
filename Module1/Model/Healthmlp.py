import argparse
import os

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

try:
    import pandas as pd
    from sklearn.model_selection import train_test_split
    HAS_PANDAS_SKLEARN = True
except ImportError:
    HAS_PANDAS_SKLEARN = False


# ---------------------------------------------------------------------------
# MODULE 1 — MLP MODEL ARCHITECTURE
# ---------------------------------------------------------------------------
HEALTH_CLASSES = ["Healthy", "Warning", "Critical"]


class HealthMLP(nn.Module):
    """
    Classifies panel condition as Healthy / Warning / Critical.

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
        # Health score: weighted combination that rewards "Healthy" probability
        health_score = float(probs[0] * 100 + probs[1] * 55 + probs[2] * 15)
        return HEALTH_CLASSES[idx], round(health_score, 1), prob_dict


# ---------------------------------------------------------------------------
# MODULE 2 — TRAINING PIPELINE (backprop + Adam, dropout/batchnorm already
# baked into the architecture above)
# ---------------------------------------------------------------------------

def load_data(csv_path: str, cnn_feature_dim: int = 128):
    """
    Expected CSV columns:
      cnn_feat_0 ... cnn_feat_{cnn_feature_dim-1}, voltage, current, power,
      temperature, efficiency, defect_confidence, historical_health_avg, label
      (label in {Healthy, Warning, Critical})
    """
    if not HAS_PANDAS_SKLEARN:
        raise RuntimeError("pandas/scikit-learn are required to load a real CSV. "
                            "pip install pandas scikit-learn")
    df = pd.read_csv(csv_path)
    cnn_cols = [f"cnn_feat_{i}" for i in range(cnn_feature_dim)]
    numeric_cols = ["voltage", "current", "power", "temperature", "efficiency",
                     "defect_confidence", "historical_health_avg"]
    X = df[cnn_cols + numeric_cols].values.astype(np.float32)
    y = df["label"].map({c: i for i, c in enumerate(HEALTH_CLASSES)}).values.astype(np.int64)
    return X, y


def make_synthetic_data(n_samples: int = 2000, cnn_feature_dim: int = 128, seed: int = 42):
    """
    Generates a synthetic dataset with the same shape/semantics as the real
    feature schema, so the training pipeline can be demonstrated end-to-end
    without a real dataset. Each class gets a distinct feature distribution
    so the model has a learnable signal.
    """
    rng = np.random.default_rng(seed)
    n_numeric = 7
    X = np.zeros((n_samples, cnn_feature_dim + n_numeric), dtype=np.float32)
    y = np.zeros(n_samples, dtype=np.int64)

    per_class = n_samples // 3
    class_centers = {
        0: dict(cnn_mean=0.0, defect_conf=0.10, eff=0.95, temp=35.0),   # Healthy
        1: dict(cnn_mean=0.5, defect_conf=0.45, eff=0.80, temp=48.0),   # Warning
        2: dict(cnn_mean=1.2, defect_conf=0.85, eff=0.55, temp=62.0),   # Critical
    }

    idx = 0
    for cls, params in class_centers.items():
        n = per_class if cls < 2 else n_samples - 2 * per_class
        cnn_feats = rng.normal(params["cnn_mean"], 1.0, size=(n, cnn_feature_dim)).astype(np.float32)

        voltage = rng.normal(32, 2, size=n).astype(np.float32)
        current = rng.normal(8, 1, size=n).astype(np.float32)
        power = voltage * current
        temperature = rng.normal(params["temp"], 5, size=n).astype(np.float32)
        efficiency = rng.normal(params["eff"], 0.05, size=n).astype(np.float32)
        defect_confidence = np.clip(rng.normal(params["defect_conf"], 0.1, size=n), 0, 1).astype(np.float32)
        historical_avg = rng.normal(100 - cls * 30, 8, size=n).astype(np.float32)

        numeric = np.stack(
            [voltage, current, power, temperature, efficiency, defect_confidence, historical_avg],
            axis=1,
        )
        X[idx:idx + n] = np.concatenate([cnn_feats, numeric], axis=1)
        y[idx:idx + n] = cls
        idx += n

    perm = rng.permutation(n_samples)
    return X[perm], y[perm]


def train(csv_path: str, epochs: int, lr: float, out_path: str, batch_size: int = 64):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[health_mlp] device = {device}")

    if csv_path and os.path.exists(csv_path):
        print(f"[health_mlp] loading real dataset from {csv_path}")
        X, y = load_data(csv_path)
    else:
        print("[health_mlp] no CSV found — generating synthetic demo dataset")
        X, y = make_synthetic_data()

    if HAS_PANDAS_SKLEARN:
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    else:
        # simple manual split if sklearn isn't available
        n_val = int(0.2 * len(X))
        idx = np.random.permutation(len(X))
        val_idx, train_idx = idx[:n_val], idx[n_val:]
        X_train, X_val, y_train, y_val = X[train_idx], X[val_idx], y[train_idx], y[val_idx]

    train_ds = TensorDataset(torch.tensor(X_train), torch.tensor(y_train))
    val_ds = TensorDataset(torch.tensor(X_val), torch.tensor(y_val))
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size)

    model = HealthMLP().to(device)

    # --- Module 2 requirements ---
    criterion = nn.CrossEntropyLoss()                       # loss used for backprop
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)  # Adam optimizer

    best_val_loss = float("inf")
    patience, epochs_no_improve = 7, 0

    for epoch in range(1, epochs + 1):
        # ---- train step (backpropagation happens via loss.backward()) ----
        model.train()
        running_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()          # backprop
            optimizer.step()         # Adam update
            running_loss += loss.item() * xb.size(0)
        train_loss = running_loss / len(train_loader.dataset)

        # ---- validation step ----
        model.eval()
        val_loss, correct = 0.0, 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                logits = model(xb)
                loss = criterion(logits, yb)
                val_loss += loss.item() * xb.size(0)
                correct += (logits.argmax(1) == yb).sum().item()
        val_loss /= len(val_loader.dataset)
        val_acc = correct / len(val_loader.dataset)

        print(f"Epoch {epoch}/{epochs} | train_loss={train_loss:.4f} val_loss={val_loss:.4f} val_acc={val_acc:.3f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            epochs_no_improve = 0
            os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
            torch.save(model.state_dict(), out_path)
            print(f"  -> saved new best model to {out_path}")
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print("Early stopping triggered.")
                break

    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the SolSight Health MLP (Modules 1 & 2)")
    parser.add_argument("--csv", default="", help="Path to a real features CSV (optional). "
                                                    "If omitted or not found, synthetic data is used.")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--out", default="mlp_best.pt")
    args = parser.parse_args()
    train(args.csv, args.epochs, args.lr, args.out)