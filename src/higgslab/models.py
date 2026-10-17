"""Small CPU classifiers and the MiniHEP event encoder.

MiniHEP follows the *teaching idea* in the masked four-vector prototype from
the October 2026 HSF-India course (source commit
76cfa28c433d1f3e9ac95c0102974a55b37de54d): hide whole object vectors, predict
them, and pool token states for a downstream probe. This implementation is a
fresh version adapted to HiggsLab's shared five-slot feature contract.
"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn


class FeatureMLP(nn.Module):
    """Compact classifier for the shared engineered feature array."""

    def __init__(self, n_features: int, width: int = 64):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(n_features, width), nn.GELU(),
            nn.Linear(width, width // 2), nn.GELU(), nn.Linear(width // 2, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x).squeeze(-1)


class MiniHEP(nn.Module):
    """Masked five-token transformer; inputs are scaled (px, py, pz, E)."""

    def __init__(self, width: int = 32, heads: int = 4, layers: int = 2,
                 dropout: float = 0.1):
        super().__init__()
        self.vector_projection = nn.Linear(4, width)
        # Slots have fixed meanings: lepton 0/1, jet 0/1, and MET proxy.
        self.slot_embedding = nn.Embedding(5, width)
        self.mask_embedding = nn.Parameter(torch.zeros(width))
        block = nn.TransformerEncoderLayer(
            d_model=width, nhead=heads, dim_feedforward=2 * width,
            dropout=dropout, activation="gelu", batch_first=True, norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(block, num_layers=layers,
                                             enable_nested_tensor=False)
        self.readout = nn.Linear(width, 4)

    def states(self, vectors: torch.Tensor, valid: torch.Tensor,
               hidden: torch.Tensor | None = None) -> torch.Tensor:
        if vectors.ndim != 3 or vectors.shape[1:] != (5, 4):
            raise ValueError("vectors must have shape (batch, 5, 4)")
        if valid.shape != vectors.shape[:2]:
            raise ValueError("valid mask must have shape (batch, 5)")
        if hidden is None:
            hidden = torch.zeros_like(valid)
        if hidden.shape != valid.shape or torch.any(hidden & ~valid):
            raise ValueError("hidden mask must match valid and cannot hide padding")
        slots = torch.arange(5, device=vectors.device).expand(vectors.shape[0], -1)
        visible = vectors.masked_fill((hidden | ~valid).unsqueeze(-1), 0.0)
        state = self.vector_projection(visible) + self.slot_embedding(slots)
        state = state + hidden.unsqueeze(-1) * self.mask_embedding
        return self.encoder(state, src_key_padding_mask=~valid)

    def forward(self, vectors: torch.Tensor, valid: torch.Tensor,
                 hidden: torch.Tensor) -> torch.Tensor:
        return self.readout(self.states(vectors, valid, hidden))

    def encode_events(self, vectors: torch.Tensor, valid: torch.Tensor) -> torch.Tensor:
        states = self.states(vectors, valid)
        return (states * valid.unsqueeze(-1)).sum(dim=1) / valid.sum(dim=1, keepdim=True).clamp_min(1)


class MiniHEPClassifier(nn.Module):
    def __init__(self, encoder: MiniHEP, width: int = 32):
        super().__init__()
        self.encoder = encoder
        self.head = nn.Sequential(nn.Linear(width, width // 2), nn.GELU(), nn.Linear(width // 2, 1))

    def forward(self, vectors: torch.Tensor, valid: torch.Tensor) -> torch.Tensor:
        return self.head(self.encoder.encode_events(vectors, valid)).squeeze(-1)


def sample_hidden(valid: torch.Tensor, probability: float,
                  generator: torch.Generator) -> torch.Tensor:
    """Hide valid whole tokens and guarantee one reconstruction target per row."""
    if not 0 < probability <= 1:
        raise ValueError("mask probability must be in (0, 1]")
    hidden = (torch.rand(valid.shape, generator=generator, device=valid.device) < probability) & valid
    empty = ~hidden.any(dim=1)
    if empty.any():
        rows = torch.nonzero(empty, as_tuple=True)[0]
        choices = torch.rand(valid[rows].shape, generator=generator, device=valid.device)
        hidden[rows, choices.masked_fill(~valid[rows], -1).argmax(dim=1)] = True
    return hidden


def state_to_json(model: nn.Module) -> dict[str, list | float | int]:
    """Convert a CPU state dict to JSON-friendly arrays."""
    return {key: value.detach().cpu().numpy().tolist() for key, value in model.state_dict().items()}


def state_from_json(model: nn.Module, values: dict) -> None:
    # Validate keys and shapes rather than silently loading a mismatched model.
    expected = model.state_dict()
    if values.keys() != expected.keys():
        raise ValueError("model weight names do not match this architecture")
    state = {key: torch.as_tensor(values[key], dtype=current.dtype)
             for key, current in expected.items()}
    model.load_state_dict(state, strict=True)


def numpy_mlp(x: np.ndarray, layers: list[dict]) -> np.ndarray:
    """Run an exported MLP with NumPy, keeping inference independent of torch."""
    result = np.asarray(x, dtype=np.float64)
    for i, layer in enumerate(layers):
        result = result @ np.asarray(layer["weight"]).T + np.asarray(layer["bias"])
        if i < len(layers) - 1:
            # GELU approximation used by torch.nn.GELU(approximate='none').
            erf = np.vectorize(__import__("math").erf, otypes=[float])
            result = 0.5 * result * (1.0 + erf(result / np.sqrt(2.0)))
    return result.reshape(-1)
