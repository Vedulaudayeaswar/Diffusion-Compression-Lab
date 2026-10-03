from pathlib import Path

import numpy as np
import torch

from backend.diffusion_codec.arithmetic import decode_symbols, encode_symbols
from backend.diffusion_codec.dfc2 import build_packet, parse_packet, symbols_from_packet
from backend.diffusion_codec.entropy import build_entropy_tables, build_entropy_tables_from_metadata
from backend.diffusion_codec.model import CompressionCodec
from backend.diffusion_codec.quantization import QuantizationParameters, inverse_quantize, quantize


ROOT = Path(__file__).resolve().parents[2]


def test_checkpoint_loads_strictly_and_matches_expected_architecture():
    codec, metadata = CompressionCodec.from_checkpoint(ROOT / "models" / "paper_style_best.pt")
    assert metadata["model_id"] == "sd-research/stable-diffusion-2-1-base"
    assert tuple(codec.estimator.features[0].weight.shape) == (64, 5, 3, 3)
    assert tuple(codec.estimator.features[8].weight.shape) == (9, 256, 3, 3)
    assert tuple(codec.entropy_model.mean.shape) == (4,)


def test_quantization_round_trip():
    latent = torch.tensor([[[[1.5]], [[-2.0]], [[0.25]], [[7.0]]]])
    params = QuantizationParameters(
        scale=torch.ones(1, 4, 1, 1),
        offset=torch.zeros(1, 4, 1, 1),
        timestep_normalized=torch.tensor([0.5]),
    )
    assert torch.equal(quantize(latent, params), torch.tensor([[[[2]], [[-2]], [[0]], [[7]]]]))
    assert torch.equal(inverse_quantize(quantize(latent, params), params.scale, params.offset), torch.tensor([[[[2.0]], [[-2.0]], [[0.0]], [[7.0]]]]))


def test_entropy_and_arithmetic_round_trip():
    symbols = np.array(
        [[[0, 1, -2], [3, 1, 0]], [[2, 2, 3], [1, 0, -1]], [[5, 5, 5], [4, 4, 4]], [[0, 0, 1], [1, 2, 3]]],
        dtype=np.int32,
    )
    tables = build_entropy_tables(symbols, np.zeros(4, dtype=np.float32), np.zeros(4, dtype=np.float32))
    payload = encode_symbols(symbols, tables.cumulatives, tables.minima)
    flat = decode_symbols(payload, symbols.size, tables.cumulatives, tables.minima)
    decoded = flat.reshape(2, 3, 4).transpose(2, 0, 1)
    assert np.array_equal(symbols, decoded)


def test_dfc2_round_trip_and_checksum():
    symbols = np.arange(24, dtype=np.int32).reshape(4, 2, 3)
    tables = build_entropy_tables(symbols, np.zeros(4, dtype=np.float32), np.zeros(4, dtype=np.float32))
    payload = encode_symbols(symbols, tables.cumulatives, tables.minima)
    metadata = {
        "channels": 4,
        "latent_height": 2,
        "latent_width": 3,
        "symbol_count": int(symbols.size),
        "symbol_minima": tables.minima.tolist(),
        "symbol_maxima": tables.maxima.tolist(),
        "entropy_mean": [0, 0, 0, 0],
        "entropy_log_scale": [0, 0, 0, 0],
    }
    packet_bytes = build_packet(metadata, payload)
    packet = parse_packet(packet_bytes)
    restored_tables = build_entropy_tables_from_metadata(
        np.asarray(packet.metadata["symbol_minima"]), np.asarray(packet.metadata["symbol_maxima"]),
        np.asarray(packet.metadata["entropy_mean"]), np.asarray(packet.metadata["entropy_log_scale"]),
    )
    assert np.array_equal(symbols, symbols_from_packet(packet, restored_tables))
    corrupted = packet_bytes[:-1] + bytes([packet_bytes[-1] ^ 1])
    try:
        parse_packet(corrupted)
    except ValueError as exc:
        assert "checksum" in str(exc)
    else:
        raise AssertionError("Corrupted DFC2 payload was accepted")
