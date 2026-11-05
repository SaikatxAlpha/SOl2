"""
Module 5 — VAE Synthetic Defect Images: Training + Generation
==============================================================
Trains the ConvVAE on the images of ONE rare defect class, then decodes
random latent vectors into new synthetic images of that class. Writing them
next to the real images grows the minority class and reduces class
imbalance before the Module 3 CNN is trained.

    data/train/Crack/*.jpg   ->   data/train/Crack/vae_0000.png ...

Usage:
    python Module5/Training/train_vae.py --class-dir data/train/Crack --epochs 50 --generate 200
"""
import argparse
import os
import sys

import torch
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.utils import save_image
from PIL import Image

# Make Module5 model importable when running this script directly
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "Model"))
from defect_vae import ConvVAE, vae_loss  # noqa: E402

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp")


class ImageFolderFlat(Dataset):
    """All images in a single folder (one defect class); skips earlier VAE outputs."""

    def __init__(self, folder: str, image_size: int):
        self.paths = sorted(
            os.path.join(folder, f) for f in os.listdir(folder)
            if f.lower().endswith(IMAGE_EXTS) and not f.startswith("vae_")
        )
        if not self.paths:
            raise SystemExit(f"No images found in {folder}")
        self.tf = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),  # 0-1, matches the decoder's Sigmoid output
        ])

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        return self.tf(Image.open(self.paths[i]).convert("RGB"))


def train(class_dir, epochs, lr, image_size, latent_dim, out_path):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    loader = DataLoader(ImageFolderFlat(class_dir, image_size), batch_size=32, shuffle=True)
    model = ConvVAE(image_size=image_size, latent_dim=latent_dim).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    for epoch in range(1, epochs + 1):
        model.train()
        total = 0.0
        for x in loader:
            x = x.to(device)
            recon, mu, logvar = model(x)
            loss = vae_loss(recon, x, mu, logvar)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += loss.item()
        print(f"Epoch {epoch:03d}  loss/image={total / len(loader.dataset):.2f}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    torch.save(model.state_dict(), out_path)
    print(f"Saved VAE to {out_path}")
    return model, device


def generate(model, device, n, out_dir):
    images = model.generate(n, device=device).cpu()
    for i, img in enumerate(images):
        save_image(img, os.path.join(out_dir, f"vae_{i:04d}.png"))
    print(f"Wrote {n} synthetic images to {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--class-dir", required=True, help="folder of one defect class, e.g. data/train/Crack")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--image-size", type=int, default=64)
    parser.add_argument("--latent-dim", type=int, default=128)
    parser.add_argument("--generate", type=int, default=100, help="synthetic images to write (0 = none)")
    parser.add_argument("--out", default=None, help="checkpoint path (default saved_models/vae_<class>.pt)")
    args = parser.parse_args()

    class_name = os.path.basename(os.path.normpath(args.class_dir))
    out = args.out or os.path.join(os.path.dirname(__file__), "..", "..", "saved_models", f"vae_{class_name.lower()}.pt")
    model, device = train(args.class_dir, args.epochs, args.lr, args.image_size, args.latent_dim, out)
    if args.generate:
        generate(model, device, args.generate, args.class_dir)
