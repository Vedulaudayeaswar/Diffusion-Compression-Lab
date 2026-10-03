from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass

import numpy as np


MAGIC = b"DFC2"
VERSION = 1
PREFIX = struct.Struct(">4sBBIQ")
CHECKSUM_SIZE = 32


@dataclass(frozen=True)
class DFC2Packet:
    metadata: dict
    payload: bytes

    @property
    def channels(self) -> int:
        return int(self.metadata["channels"])

    @property
    def symbol_count(self) -> int:
        return int(self.metadata["symbol_count"])

    def symbols_shape(self) -> tuple[int, int, int, int]:
        return (
            1,
            self.channels,
            int(self.metadata["latent_height"]),
            int(self.metadata["latent_width"]),
        )


def build_packet(metadata: dict, payload: bytes) -> bytes:
    serializable = dict(metadata)
    serializable["payload_bit_length"] = len(payload) * 8
    serializable["payload_byte_length"] = len(payload)
    metadata_bytes = json.dumps(serializable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    prefix = PREFIX.pack(MAGIC, VERSION, 0, len(metadata_bytes), len(payload))
    body = prefix + metadata_bytes + payload
    return body + hashlib.sha256(body).digest()


def parse_packet(data: bytes) -> DFC2Packet:
    if len(data) < PREFIX.size + CHECKSUM_SIZE:
        raise ValueError("DFC2 file is too short")
    prefix = data[: PREFIX.size]
    magic, version, _reserved, metadata_length, payload_length = PREFIX.unpack(prefix)
    if magic != MAGIC:
        raise ValueError("Invalid DFC2 magic")
    if version != VERSION:
        raise ValueError(f"Unsupported DFC2 version: {version}")
    end_body = PREFIX.size + metadata_length + payload_length
    if len(data) != end_body + CHECKSUM_SIZE:
        raise ValueError("DFC2 length does not match its header")
    body, checksum = data[:end_body], data[end_body:]
    if hashlib.sha256(body).digest() != checksum:
        raise ValueError("DFC2 checksum mismatch")
    try:
        metadata = json.loads(data[PREFIX.size : PREFIX.size + metadata_length].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("DFC2 metadata is invalid") from exc
    if metadata.get("payload_byte_length") != payload_length:
        raise ValueError("DFC2 payload length metadata mismatch")
    return DFC2Packet(metadata, data[PREFIX.size + metadata_length : end_body])


def symbols_from_packet(packet: DFC2Packet, tables) -> np.ndarray:
    from .arithmetic import decode_symbols

    flat = decode_symbols(packet.payload, packet.symbol_count, tables.cumulatives, tables.minima)
    h, w = int(packet.metadata["latent_height"]), int(packet.metadata["latent_width"])
    return flat.reshape(h, w, packet.channels).transpose(2, 0, 1)
