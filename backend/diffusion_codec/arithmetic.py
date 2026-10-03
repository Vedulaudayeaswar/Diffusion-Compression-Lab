from __future__ import annotations

import numpy as np


_TOP = (1 << 32) - 1
_HALF = 1 << 31
_FIRST_QTR = 1 << 30
_THIRD_QTR = 3 << 30


class _BitWriter:
    def __init__(self) -> None:
        self.bits: list[int] = []

    def write(self, bit: int) -> None:
        self.bits.append(bit & 1)

    def finish(self) -> bytes:
        while len(self.bits) % 8:
            self.bits.append(0)
        out = bytearray()
        for i in range(0, len(self.bits), 8):
            value = 0
            for bit in self.bits[i : i + 8]:
                value = (value << 1) | bit
            out.append(value)
        return bytes(out)


class _BitReader:
    def __init__(self, payload: bytes) -> None:
        self.bits = [(byte >> shift) & 1 for byte in payload for shift in range(7, -1, -1)]
        self.index = 0

    def read(self) -> int:
        if self.index >= len(self.bits):
            return 0
        bit = self.bits[self.index]
        self.index += 1
        return bit


def _emit_with_follow(writer: _BitWriter, bit: int, pending: int) -> None:
    writer.write(bit)
    for _ in range(pending):
        writer.write(1 - bit)


def encode_symbols(symbols: np.ndarray, cumulatives: list[np.ndarray], minima: np.ndarray) -> bytes:
    array = np.asarray(symbols, dtype=np.int64)
    if array.ndim != 3:
        raise ValueError("Expected symbols with shape [channels, height, width]")
    # Interleave channels per spatial position so channel = index % C is
    # deterministic and decoder metadata stays compact.
    flat = array.transpose(1, 2, 0).reshape(-1)
    low, high, pending = 0, _TOP, 0
    writer = _BitWriter()
    channels = len(cumulatives)
    for index, symbol in enumerate(flat):
        channel = index % channels
        cdf = cumulatives[channel]
        offset = int(symbol) - int(minima[channel])
        if offset < 0 or offset >= len(cdf) - 1:
            raise ValueError("Symbol outside entropy alphabet")
        total = int(cdf[-1])
        interval = high - low + 1
        high = low + (interval * int(cdf[offset + 1])) // total - 1
        low = low + (interval * int(cdf[offset])) // total
        while True:
            if high < _HALF:
                _emit_with_follow(writer, 0, pending)
                pending = 0
            elif low >= _HALF:
                _emit_with_follow(writer, 1, pending)
                pending = 0
                low -= _HALF
                high -= _HALF
            elif low >= _FIRST_QTR and high < _THIRD_QTR:
                pending += 1
                low -= _FIRST_QTR
                high -= _FIRST_QTR
            else:
                break
            low = (low << 1) & _TOP
            high = ((high << 1) | 1) & _TOP
    pending += 1
    if low < _FIRST_QTR:
        _emit_with_follow(writer, 0, pending)
    else:
        _emit_with_follow(writer, 1, pending)
    return writer.finish()


def decode_symbols(payload: bytes, count: int, cumulatives: list[np.ndarray], minima: np.ndarray) -> np.ndarray:
    reader = _BitReader(payload)
    low, high, code = 0, _TOP, 0
    for _ in range(32):
        code = ((code << 1) | reader.read()) & _TOP
    output = np.empty(count, dtype=np.int32)
    channels = len(cumulatives)
    for index in range(count):
        channel = index % channels
        cdf = cumulatives[channel]
        total = int(cdf[-1])
        interval = high - low + 1
        value = ((code - low + 1) * total - 1) // interval
        symbol_index = int(np.searchsorted(cdf, value, side="right") - 1)
        if symbol_index < 0 or symbol_index >= len(cdf) - 1:
            raise ValueError("Arithmetic payload decoded outside entropy alphabet")
        output[index] = int(minima[channel]) + symbol_index
        high = low + (interval * int(cdf[symbol_index + 1])) // total - 1
        low = low + (interval * int(cdf[symbol_index])) // total
        while True:
            if high < _HALF:
                pass
            elif low >= _HALF:
                low -= _HALF
                high -= _HALF
                code -= _HALF
            elif low >= _FIRST_QTR and high < _THIRD_QTR:
                low -= _FIRST_QTR
                high -= _FIRST_QTR
                code -= _FIRST_QTR
            else:
                break
            low = (low << 1) & _TOP
            high = ((high << 1) | 1) & _TOP
            code = ((code << 1) | reader.read()) & _TOP
    return output
