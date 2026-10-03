from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import torch


TOTAL_FREQUENCY = 1 << 20


@dataclass(frozen=True)
class EntropyTables:
    frequencies: list[np.ndarray]
    cumulatives: list[np.ndarray]
    minima: np.ndarray
    maxima: np.ndarray
    means: np.ndarray
    log_scales: np.ndarray

    @property
    def channels(self) -> int:
        return len(self.frequencies)


def _normal_cdf(x: float, mean: float, scale: float) -> float:
    return 0.5 * (1.0 + math.erf((x - mean) / (scale * math.sqrt(2.0))))


def gaussian_symbol_probability(symbol: int, mean: float, scale: float) -> float:
    return max(0.0, _normal_cdf(symbol + 0.5, mean, scale) - _normal_cdf(symbol - 0.5, mean, scale))


def build_entropy_tables(
    symbols: np.ndarray,
    means: np.ndarray,
    log_scales: np.ndarray,
    total_frequency: int = TOTAL_FREQUENCY,
) -> EntropyTables:
    channels = symbols.shape[0]
    minima = symbols.reshape(channels, -1).min(axis=1).astype(np.int32)
    maxima = symbols.reshape(channels, -1).max(axis=1).astype(np.int32)
    frequency_tables: list[np.ndarray] = []
    cumulative_tables: list[np.ndarray] = []
    for channel in range(channels):
        lo, hi = int(minima[channel]), int(maxima[channel])
        scale = float(math.exp(float(log_scales[channel])))
        mean = float(means[channel])
        probs = np.array(
            [gaussian_symbol_probability(k, mean, scale) for k in range(lo, hi + 1)],
            dtype=np.float64,
        )
        # Tails outside the observed alphabet are not needed because the file
        # carries the exact observed symbol range. Normalize the modeled mass
        # so the integer table remains stable and sums to a useful total.
        if not np.isfinite(probs).all() or probs.sum() <= 0:
            probs = np.ones_like(probs, dtype=np.float64)
        probs /= probs.sum()
        freqs = np.maximum(1, np.rint(probs * total_frequency).astype(np.int64))
        cumulative = np.concatenate(([0], np.cumsum(freqs, dtype=np.int64)))
        frequency_tables.append(freqs)
        cumulative_tables.append(cumulative)
    return EntropyTables(
        frequency_tables,
        cumulative_tables,
        minima,
        maxima,
        means.astype(np.float32),
        log_scales.astype(np.float32),
    )


def build_entropy_tables_from_metadata(
    minima: np.ndarray,
    maxima: np.ndarray,
    means: np.ndarray,
    log_scales: np.ndarray,
) -> EntropyTables:
    frequency_tables: list[np.ndarray] = []
    cumulative_tables: list[np.ndarray] = []
    for lo, hi, mean, log_scale in zip(minima, maxima, means, log_scales):
        low, high = int(lo), int(hi)
        scale = float(math.exp(float(log_scale)))
        probs = np.array(
            [gaussian_symbol_probability(k, float(mean), scale) for k in range(low, high + 1)],
            dtype=np.float64,
        )
        if not np.isfinite(probs).all() or probs.sum() <= 0:
            probs = np.ones_like(probs, dtype=np.float64)
        probs /= probs.sum()
        freqs = np.maximum(1, np.rint(probs * TOTAL_FREQUENCY).astype(np.int64))
        frequency_tables.append(freqs)
        cumulative_tables.append(np.concatenate(([0], np.cumsum(freqs, dtype=np.int64))))
    return EntropyTables(
        frequency_tables,
        cumulative_tables,
        np.asarray(minima, dtype=np.int32),
        np.asarray(maxima, dtype=np.int32),
        np.asarray(means, dtype=np.float32),
        np.asarray(log_scales, dtype=np.float32),
    )
