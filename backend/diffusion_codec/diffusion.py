from __future__ import annotations

import torch


def interpolate_alpha_bar(scheduler, timestep_normalized: torch.Tensor) -> torch.Tensor:
    alpha = scheduler.alphas_cumprod.to(device=timestep_normalized.device, dtype=torch.float32)
    position = timestep_normalized.float().clamp(0, 1) * (len(alpha) - 1)
    low = position.floor().long().clamp(0, len(alpha) - 1)
    high = position.ceil().long().clamp(0, len(alpha) - 1)
    weight = position - low.float()
    return alpha[low] + weight * (alpha[high] - alpha[low])


@torch.inference_mode()
def reconstruct_latent(unet, scheduler, latent: torch.Tensor, timestep_normalized: torch.Tensor) -> torch.Tensor:
    alpha_bar = interpolate_alpha_bar(scheduler, timestep_normalized).view(-1, 1, 1, 1)
    timestep = timestep_normalized * (len(scheduler.alphas_cumprod) - 1)
    context = torch.zeros(
        (latent.shape[0], 77, 1024), device=latent.device, dtype=latent.dtype
    )
    noise_pred = unet(latent, timestep, encoder_hidden_states=context).sample
    return (latent.float() - torch.sqrt(1.0 - alpha_bar) * noise_pred.float()) / torch.sqrt(alpha_bar)
