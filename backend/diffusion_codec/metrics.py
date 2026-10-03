from __future__ import annotations

import math
import time
from pathlib import Path

import numpy as np
from PIL import Image


def image_array(path_or_image) -> np.ndarray:
    if isinstance(path_or_image, Image.Image):
        image = path_or_image
    else:
        image = Image.open(path_or_image)
    return np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0


def calculate_image_metrics(original, reconstructed) -> tuple[float, float, float | None]:
    a, b = image_array(original), image_array(reconstructed)
    if a.shape != b.shape:
        b = np.asarray(Image.fromarray((b * 255).astype(np.uint8)).resize((a.shape[1], a.shape[0]))) / 255.0
    mse = float(np.mean((a - b) ** 2))
    psnr = float("inf") if mse == 0 else float(10.0 * math.log10(1.0 / mse))
    ssim = None
    try:
        from skimage.metrics import structural_similarity

        ssim = float(structural_similarity(a, b, channel_axis=2, data_range=1.0))
    except Exception:
        pass
    return mse, psnr, ssim


def file_metrics(original_path: Path, dfc2_path: Path, reconstruction_path: Path, width: int, height: int) -> dict:
    original_size = original_path.stat().st_size
    compressed_size = dfc2_path.stat().st_size
    return {
        "original_file_size": original_size,
        "compressed_file_size": compressed_size,
        "bpp": compressed_size * 8 / (width * height),
        "compression_ratio": original_size / compressed_size if compressed_size else None,
        "latent_shape": None,
    }
