"""
Train the HealthMLP on a CSV of pre-extracted features + labels.

Expected CSV columns:
  cnn_feat_0 ... cnn_feat_127, voltage, current, power, temperature,
  efficiency, defect_confidence, historical_health_avg, label
  (label in {Healthy, Warning, Critical})

Usage:
    python train_mlp.py --csv data/mlp_features.csv --epochs 50 --out ../saved_models/mlp_best.pt
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from torch.utils.data import TensorDataset, DataLoader

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from app.models.mlp_model import HealthMLP, HEALTH_CLASSES  # noqa: E402


def load_data(csv_path: str, cnn_feature_dim: int = 128):
    df = pd.read_csv(csv_path)
    cnn_cols = [f"cnn_feat_{i}" for i in range(cnn_feature_dim)]
    numeric_cols = ["voltage", "current", "power", "temperature", "efficiency",
                     "defect_confidence", "historical_health_avg"]
    X = df[cnn_cols + numeric_cols].values.astype(np.float32)
    y = df["label"].map({c: i for i, c in enumerate(HEALTH_CLASSES)}).values.astype(np.int64)
    return X, y


def train(csv_path: str, epochs: int, lr: float, out_path: str, batch_size: int = 64):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    X, y = load_data(csv_path)
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    train_ds = TensorDataset(torch.tensor(X_train), torch.tensor(y_train))
    val_ds = TensorDataset(torch.tensor(X_val), torch.tensor(y_val))
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size)

    model = HealthMLP().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)

    best_val_loss = float("inf")
    patience, epochs_no_improve = 7, 0

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * xb.size(0)
        train_loss = running_loss / len(train_loader.dataset)

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
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            torch.save(model.state_dict(), out_path)
            print(f"  -> saved new best model to {out_path}")
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print("Early stopping triggered.")
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/mlp_features.csv")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--out", default="../saved_models/mlp_best.pt")
    args = parser.parse_args()
    train(args.csv, args.epochs, args.lr, args.out)