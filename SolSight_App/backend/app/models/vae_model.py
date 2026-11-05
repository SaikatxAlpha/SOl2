"""
Variational Autoencoder used offline (during dataset preparation / training)
to generate synthetic images of rare defect classes (Crack, Hotspot) so the
CNN doesn't overfit to the majority "Normal"/"Soiling" classes.

NOT used in the live inference path -- only in ml_training/ scripts.
"""
import torch
import torch.nn as nn


class ConvVAE(nn.Module):
    def __init__(self, image_size: int = 64, latent_dim: int = 128):
        super().__init__()
        self.image_size = image_size
        self.latent_dim = latent_dim

        self.encoder = nn.Sequential(
            nn.Conv2d(3, 32, 4, stride=2, padding=1), nn.ReLU(),   # 32x32
            nn.Conv2d(32, 64, 4, stride=2, padding=1), nn.ReLU(),  # 16x16
            nn.Conv2d(64, 128, 4, stride=2, padding=1), nn.ReLU(), # 8x8
            nn.Flatten(),
        )
        flat_dim = 128 * (image_size // 8) * (image_size // 8)
        self.fc_mu = nn.Linear(flat_dim, latent_dim)
        self.fc_logvar = nn.Linear(flat_dim, latent_dim)

        self.decoder_input = nn.Linear(latent_dim, flat_dim)
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(128, 64, 4, stride=2, padding=1), nn.ReLU(),
            nn.ConvTranspose2d(64, 32, 4, stride=2, padding=1), nn.ReLU(),
            nn.ConvTranspose2d(32, 3, 4, stride=2, padding=1), nn.Sigmoid(),
        )
        self._unflatten_shape = (128, image_size // 8, image_size // 8)

    def encode(self, x):
        h = self.encoder(x)
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode(self, z):
        h = self.decoder_input(z)
        h = h.view(-1, *self._unflatten_shape)
        return self.decoder(h)

    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        recon = self.decode(z)
        return recon, mu, logvar

    @torch.no_grad()
    def generate(self, num_samples: int = 1, device="cpu"):
        z = torch.randn(num_samples, self.latent_dim, device=device)
        return self.decode(z)


def vae_loss(recon_x, x, mu, logvar):
    recon_loss = nn.functional.binary_cross_entropy(recon_x, x, reduction="sum")
    kld = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
    return recon_loss + kld