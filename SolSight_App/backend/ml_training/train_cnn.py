"""
Train the DefectCNN on a labeled folder-per-class image dataset:

    data/
      train/
        Normal/*.jpg
        Crack/*.jpg
        Hotspot/*.jpg
        Soiling/*.jpg
      val/
        Normal/*.jpg
        ...

Usage:
    python train_cnn.py --data-dir data --epochs 20 --out ../saved_models/cnn_best.pt
"""
import argparse
import os
import sys

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from app.models.cnn_model import DefectCNN, IMAGE_SIZE, DEFECT_CLASSES  # noqa: E402


def get_dataloaders(data_dir: str, batch_size: int = 32):
    train_tf = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    train_ds = datasets.ImageFolder(os.path.join(data_dir, "train"), transform=train_tf)
    val_ds = datasets.ImageFolder(os.path.join(data_dir, "val"), transform=val_tf)
    return (
        DataLoader(train_ds, batch_size=batch_size, shuffle=True),
        DataLoader(val_ds, batch_size=batch_size),
        train_ds.classes,
    )


def train(data_dir: str, epochs: int, lr: float, out_path: str, patience: int = 5):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader, val_loader, classes = get_dataloaders(data_dir)
    assert classes == DEFECT_CLASSES or set(classes) == set(DEFECT_CLASSES), \
        f"Dataset classes {classes} don't match expected {DEFECT_CLASSES}"

    model = DefectCNN(num_classes=len(classes), pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", patience=2)

    best_val_loss = float("inf")
    epochs_no_improve = 0

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            logits = model(imgs)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * imgs.size(0)
        train_loss = running_loss / len(train_loader.dataset)

        model.eval()
        val_loss, correct = 0.0, 0
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                logits = model(imgs)
                loss = criterion(logits, labels)
                val_loss += loss.item() * imgs.size(0)
                correct += (logits.argmax(1) == labels).sum().item()
        val_loss /= len(val_loader.dataset)
        val_acc = correct / len(val_loader.dataset)
        scheduler.step(val_loss)

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
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--out", default="../saved_models/cnn_best.pt")
    args = parser.parse_args()
    train(args.data_dir, args.epochs, args.lr, args.out)