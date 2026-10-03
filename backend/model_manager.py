from __future__ import annotations

import threading
import traceback
from typing import Any

import torch

from .config import settings
from .diffusion_codec.model import CompressionCodec


class ModelManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded = False
        self._error: str | None = None
        self.codec = None
        self.vae = None
        self.unet = None
        self.scheduler = None
        self.checkpoint_meta: dict[str, Any] = {}

    def load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            if self._error:
                raise RuntimeError(self._error)
            try:
                codec, meta = CompressionCodec.from_checkpoint(settings.checkpoint)
                expected = meta.get("model_id", settings.model_id)
                if expected != settings.model_id:
                    raise ValueError(
                        f"Checkpoint expects {expected}, but configuration requests {settings.model_id}"
                    )
                self.codec = codec.to(dtype=torch.float32, device=settings.resolved_device).eval()
                self.checkpoint_meta = meta
                from diffusers import AutoencoderKL, DDIMScheduler, UNet2DConditionModel

                device = settings.resolved_device
                dtype = settings.torch_dtype if device != "cpu" else torch.float32
                token = settings.hf_token
                load_kwargs = {"token": token} if token else {}
                self.vae = AutoencoderKL.from_pretrained(
                    settings.model_id, subfolder="vae", torch_dtype=dtype, **load_kwargs
                ).to(device).eval()
                self.unet = UNet2DConditionModel.from_pretrained(
                    settings.model_id, subfolder="unet", torch_dtype=dtype, **load_kwargs
                ).to(device).eval()
                self.scheduler = DDIMScheduler.from_pretrained(settings.model_id, subfolder="scheduler", **load_kwargs)
                self._loaded = True
            except Exception as exc:
                self._error = f"Model loading failed: {exc}"
                raise RuntimeError(self._error) from exc

    def status(self) -> dict[str, Any]:
        return {
            "model_id": settings.model_id,
            "vae_loaded": self.vae is not None,
            "unet_loaded": self.unet is not None,
            "codec_loaded": self.codec is not None,
            "scheduler_loaded": self.scheduler is not None,
            "device": settings.resolved_device,
            "dtype": str(settings.torch_dtype if settings.resolved_device != "cpu" else torch.float32).replace("torch.", ""),
            "checkpoint": str(settings.checkpoint),
            "checkpoint_size": settings.checkpoint_size,
            "checkpoint_metadata": {
                key: value
                for key, value in self.checkpoint_meta.items()
                if key not in {"codec_state_dict", "optimizer_state_dict"}
            },
            "status": "ready" if self._loaded else ("error" if self._error else "not_loaded"),
            "error": self._error,
        }


model_manager = ModelManager()
