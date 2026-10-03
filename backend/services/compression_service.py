from __future__ import annotations

import io
import json
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
from PIL import Image

from ..config import settings
from ..diffusion_codec.arithmetic import encode_symbols
from ..diffusion_codec.dfc2 import build_packet, parse_packet, symbols_from_packet
from ..diffusion_codec.diffusion import reconstruct_latent
from ..diffusion_codec.entropy import build_entropy_tables, build_entropy_tables_from_metadata
from ..diffusion_codec.metrics import calculate_image_metrics
from ..diffusion_codec.quantization import (
    inverse_quantize,
    predict_parameters,
    quantize,
)
from ..model_manager import model_manager


Progress = Callable[..., None]


def _progress(callback: Progress | None, stage: str, value: int) -> None:
    if callback:
        callback(stage=stage, progress=value)


def _preprocess(image_bytes: bytes, resolution: int) -> tuple[Image.Image, torch.Tensor]:
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise ValueError("The uploaded file is not a valid PNG, JPEG, or WEBP image") from exc
    image = image.resize((resolution, resolution), Image.Resampling.LANCZOS)
    array = np.asarray(image, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)
    tensor = tensor * 2.0 - 1.0
    return image, tensor


def _to_image(decoded: torch.Tensor) -> Image.Image:
    array = decoded.detach().float().clamp(0, 1)[0].permute(1, 2, 0).cpu().numpy()
    return Image.fromarray(np.rint(array * 255).astype(np.uint8), mode="RGB")


def _decode_packet(packet_bytes: bytes, callback: Progress | None = None) -> tuple[Image.Image, dict[str, Any]]:
    packet = parse_packet(packet_bytes)
    metadata = packet.metadata
    tables = build_entropy_tables_from_metadata(
        np.asarray(metadata["symbol_minima"], dtype=np.int32),
        np.asarray(metadata["symbol_maxima"], dtype=np.int32),
        np.asarray(metadata["entropy_mean"], dtype=np.float32),
        np.asarray(metadata["entropy_log_scale"], dtype=np.float32),
    )
    _progress(callback, "entropy_decoding", 48)
    symbols = symbols_from_packet(packet, tables)
    manager = model_manager
    manager.load()
    device = settings.resolved_device
    scale = torch.tensor(metadata["quantization_scales"], device=device, dtype=torch.float32).view(1, -1, 1, 1)
    offset = torch.tensor(metadata["quantization_offsets"], device=device, dtype=torch.float32).view(1, -1, 1, 1)
    quantized = torch.from_numpy(symbols).unsqueeze(0).to(device)
    latent = inverse_quantize(quantized, scale, offset)
    _progress(callback, "diffusion", 64)
    with torch.inference_mode():
        reconstructed_latent = reconstruct_latent(
            manager.unet,
            manager.scheduler,
            latent.to(next(manager.unet.parameters()).dtype),
            torch.tensor([metadata["timestep_normalized"]], device=device),
        )
        _progress(callback, "vae_decoding", 82)
        decoded = manager.vae.decode(
            reconstructed_latent.to(next(manager.vae.parameters()).dtype) / manager.vae.config.scaling_factor
        ).sample
    return _to_image((decoded + 1.0) / 2.0), metadata


def compress_bytes(
    image_bytes: bytes,
    filename: str,
    job_id: str,
    *,
    mode: str = "research",
    bitrate: float | None = None,
    lambda_value: float = 5.0,
    steps: int = 1,
    resolution: int = 256,
    reconstruction_mode: str = "one_step",
    refinement_alpha: float = 0.0,
    callback: Progress | None = None,
) -> dict[str, Any]:
    del mode, bitrate, reconstruction_mode, refinement_alpha
    started = time.perf_counter()
    original_image, image_tensor = _preprocess(image_bytes, resolution)
    _progress(callback, "vae_encoding", 14)
    model_manager.load()
    device = settings.resolved_device
    with torch.inference_mode():
        vae_input = image_tensor.to(device=device, dtype=next(model_manager.vae.parameters()).dtype)
        posterior = model_manager.vae.encode(vae_input).latent_dist
        latent = posterior.mean * model_manager.vae.config.scaling_factor
    _progress(callback, "parameter_estimation", 26)
    latent_codec = latent.float()
    params = predict_parameters(model_manager.codec.estimator, latent_codec, lambda_value)
    _progress(callback, "quantization", 38)
    quantized = quantize(latent_codec, params)
    symbols = quantized[0].detach().cpu().numpy().astype(np.int32)
    means = model_manager.codec.entropy_model.mean.detach().cpu().numpy().astype(np.float32)
    log_scales = model_manager.codec.entropy_model.log_scale.detach().cpu().numpy().astype(np.float32)
    tables = build_entropy_tables(symbols, means, log_scales)
    _progress(callback, "entropy_coding", 46)
    payload = encode_symbols(symbols, tables.cumulatives, tables.minima)
    metadata = {
        "channels": int(symbols.shape[0]),
        "image_height": int(resolution),
        "image_width": int(resolution),
        "latent_height": int(symbols.shape[1]),
        "latent_width": int(symbols.shape[2]),
        "timestep_normalized": float(params.timestep_normalized[0].item()),
        "quantization_scales": params.scale[0, :, 0, 0].detach().cpu().tolist(),
        "quantization_offsets": params.offset[0, :, 0, 0].detach().cpu().tolist(),
        "entropy_mean": means.tolist(),
        "entropy_log_scale": log_scales.tolist(),
        "symbol_minima": tables.minima.tolist(),
        "symbol_maxima": tables.maxima.tolist(),
        "symbol_count": int(symbols.size),
        "source_filename": Path(filename).name,
        "lambda_value": float(lambda_value),
        "diffusion_steps": int(steps),
        "codec_checkpoint": Path(settings.checkpoint).name,
    }
    dfc2_bytes = build_packet(metadata, payload)
    dfc2_path = settings.output_dir / f"{job_id}.dfc2"
    reconstruction_path = settings.output_dir / f"{job_id}_reconstruction.png"
    dfc2_path.write_bytes(dfc2_bytes)
    _progress(callback, "dfc2_generation", 55)
    encode_elapsed = time.perf_counter() - started
    decode_started = time.perf_counter()
    reconstruction, _ = _decode_packet(dfc2_bytes, callback)
    decode_elapsed = time.perf_counter() - decode_started
    reconstruction.save(reconstruction_path, format="PNG")
    _progress(callback, "metrics", 94)
    mse, psnr, ssim = calculate_image_metrics(original_image, reconstruction)
    metrics = {
        "original_file_size": len(image_bytes),
        "compressed_file_size": len(dfc2_bytes),
        "payload_size": len(payload),
        "header_size": len(dfc2_bytes) - len(payload) - 32,
        "bpp": len(dfc2_bytes) * 8 / (resolution * resolution),
        "compression_ratio": len(image_bytes) / len(dfc2_bytes),
        "mse": mse,
        "psnr": psnr,
        "ssim": ssim,
        "encode_time_seconds": encode_elapsed,
        "decode_time_seconds": decode_elapsed,
        "latent_shape": [1, *symbols.shape],
        "diffusion_timestep": metadata["timestep_normalized"],
        "diffusion_steps": int(steps),
    }
    return {
        "metrics": metrics,
        "dfc2_path": str(dfc2_path),
        "reconstruction_path": str(reconstruction_path),
        "metadata": metadata,
    }


def decompress_bytes(packet_bytes: bytes, callback: Progress | None = None) -> tuple[bytes, dict[str, Any]]:
    started = time.perf_counter()
    image, metadata = _decode_packet(packet_bytes, callback)
    output = io.BytesIO()
    image.save(output, format="PNG")
    metadata = dict(metadata)
    metadata["decode_time_seconds"] = time.perf_counter() - started
    return output.getvalue(), metadata
