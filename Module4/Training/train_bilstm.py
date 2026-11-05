"""
Module 4 — Bi-LSTM Degradation Trend: Training
===============================================
Train the DegradationBiLSTM on historical per-panel health-score sequences.

Expected CSV format (long form, one row per inspection):
  panel_id, date, health_score

The script builds sliding windows per panel: given a window of past health
scores, predict health at +30 / +60 / +90 days (interpolated from the
sequence's known future points).

Usage:
    python Module4/Training/train_bilstm.py --csv data/health_history.csv --epochs 100
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import train_test_split

# Make Module4 model importable when running this script directly
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "Model"))
from degradation_bilstm import DegradationBiLSTM, FORECAST_HORIZONS_DAYS  # noqa: E402

WINDOW = 5


def build_sequences(csv_path: str):
    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df.sort_values(["panel_id", "date"])

    X, Y = [], []
    for panel_id, group in df.groupby("panel_id"):
        scores = group["health_score"].values
        dates = group["date"].values
        if len(scores) < WINDOW + 1:
            continue
        for i in range(WINDOW, len(scores)):
            window = scores[i - WINDOW:i]
            base_date = dates[i - 1]
            # Skip windows whose longest horizon runs past the end of the
            # data -- clamping to the last point would teach "no decline".
            if base_date + np.timedelta64(FORECAST_HORIZONS_DAYS[-1], "D") > dates[-1]:
                break
            targets = []
            for horizon in FORECAST_HORIZONS_DAYS:
                target_date = base_date + np.timedelta64(horizon, "D")
                future_idx = np.searchsorted(dates, target_date)
                # Same target the model is read with at inference time:
                # fractional decline from the last observed score.
                targets.append((window[-1] - scores[future_idx]) / 100.0)
            X.append(window)
            Y.append(targets)
    return np.array(X, dtype=np.float32), np.array(Y, dtype=np.float32)


def train(csv_path: str, epochs: int, lr: float, out_path: str, batch_size: int = 32):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    X, Y = build_sequences(csv_path)
    X = X / 100.0  # normalize health scores to 0-1
    X_train, X_val, Y_train, Y_val = train_test_split(X, Y, test_size=0.2, random_state=42)

    train_ds = TensorDataset(torch.tensor(X_train).unsqueeze(-1), torch.tensor(Y_train))
    val_ds = TensorDataset(torch.tensor(X_val).unsqueeze(-1), torch.tensor(Y_val))
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size)

    model = DegradationBiLSTM().to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    best_val_loss = float("inf")
    patience, epochs_no_improve = 10, 0

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            preds = model(xb)  # fractional decline per horizon
            loss = criterion(preds, yb)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * xb.size(0)
        train_loss = running_loss / len(train_loader.dataset)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                preds = model(xb)
                loss = criterion(preds, yb)
                val_loss += loss.item() * xb.size(0)
        val_loss /= len(val_loader.dataset)

        print(f"Epoch {epoch}/{epochs} | train_loss={train_loss:.4f} val_loss={val_loss:.4f}")

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
    parser.add_argument("--csv", default="data/health_history.csv")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "..", "saved_models", "bilstm_best.pt"))
    args = parser.parse_args()
    train(args.csv, args.epochs, args.lr, args.out)