import os

import pytest

from backend.model_manager import model_manager


@pytest.mark.skipif(os.getenv("RUN_SD21_TESTS") != "1", reason="Set RUN_SD21_TESTS=1 to download/load SD 2.1")
def test_sd21_model_loading():
    model_manager.load()
    assert model_manager.vae is not None
    assert model_manager.unet is not None
    assert model_manager.scheduler is not None

