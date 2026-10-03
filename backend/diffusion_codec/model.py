from __future__ import annotations

from pathlib import Path

import torch
from torch import nn


class ParameterEstimator(nn.Module):
    """The estimator topology used by paper_style_best.pt.

    State-dict inspection showed convolution weights at feature indices
    0, 2, 4, 6, and 8. The intervening activations are not parameterized.
    """

    def __init__(self) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(5, 64, 3, padding=1),
            nn.GELU(),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.GELU(),
            nn.Conv2d(128, 192, 3, stride=2, padding=1),
            nn.GELU(),
            nn.Conv2d(192, 256, 3, stride=2, padding=1),
            nn.GELU(),
            nn.Conv2d(256, 9, 3, padding=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.features(x).mean(dim=(-2, -1))


class EntropyModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.log_scale = nn.Parameter(torch.zeros(4))
        self.mean = nn.Parameter(torch.zeros(4))


class CompressionCodec(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.estimator = ParameterEstimator()
        self.entropy_model = EntropyModel()

    @classmethod
    def from_checkpoint(cls, path: Path) -> tuple["CompressionCodec", dict]:
        if not path.exists():
            raise FileNotFoundError(f"Compression checkpoint not found: {path}")
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        state = checkpoint.get("codec_state_dict")
        if not isinstance(state, dict):
            raise ValueError("Checkpoint does not contain codec_state_dict")
        codec = cls()
        # Strict loading is intentional: a mismatch is an architectural error.
        codec.load_state_dict(state, strict=True)
        codec.eval()
        return codec, checkpoint
