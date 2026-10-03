from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class QuantizationParameters:
    scale: torch.Tensor
    offset: torch.Tensor
    timestep_normalized: torch.Tensor


def predict_parameters(estimator, latent: torch.Tensor, lambda_value: float) -> QuantizationParameters:
    b, _, h, w = latent.shape
    condition = torch.full(
        (b, 1, h, w), float(lambda_value), device=latent.device, dtype=latent.dtype
    )
    raw = estimator(torch.cat([latent, condition], dim=1))
    scale = raw[:, :4].clamp(0.05, 2.0).view(b, 4, 1, 1)
    offset = raw[:, 4:8].view(b, 4, 1, 1)
    timestep_normalized = raw[:, 8].sigmoid().clamp(0.0, 1.0)
    return QuantizationParameters(scale, offset, timestep_normalized)


def quantize(latent: torch.Tensor, params: QuantizationParameters) -> torch.Tensor:
    return torch.round((latent - params.offset) / params.scale).to(torch.int32)


def inverse_quantize(symbols: torch.Tensor, scale: torch.Tensor, offset: torch.Tensor) -> torch.Tensor:
    return symbols.to(scale.dtype) * scale + offset
