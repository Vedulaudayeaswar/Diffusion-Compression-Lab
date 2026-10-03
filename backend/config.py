from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    model_id: str = os.getenv("DIFFUSIONCOMPRESS_MODEL_ID", "sd-research/stable-diffusion-2-1-base")
    checkpoint: Path = ROOT_DIR / os.getenv("DIFFUSIONCOMPRESS_CODEC_CHECKPOINT", "models/paper_style_best.pt")
    device: str = os.getenv("DIFFUSIONCOMPRESS_DEVICE", "cuda")
    dtype_name: str = os.getenv("DIFFUSIONCOMPRESS_DTYPE", "float16")
    output_dir: Path = ROOT_DIR / "outputs"
    hf_token: str | None = os.getenv("HF_TOKEN") or None

    @property
    def checkpoint_size(self) -> int | None:
        try:
            return self.checkpoint.stat().st_size
        except OSError:
            return None

    @property
    def resolved_device(self) -> str:
        import torch

        if self.device.startswith("cuda") and not torch.cuda.is_available():
            return "cpu"
        return self.device

    @property
    def torch_dtype(self):
        import torch

        if self.dtype_name == "float16":
            return torch.float16
        if self.dtype_name == "bfloat16":
            return torch.bfloat16
        return torch.float32


settings = Settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)
