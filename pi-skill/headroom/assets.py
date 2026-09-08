"""Pinned public ONNX assets; no runtime downloads or executable model code."""
import hashlib
from pathlib import Path

REPOSITORY = "Qdrant/all-MiniLM-L6-v2-onnx"
REVISION = "5f1b8cd78bc4fb444dd171e59b18f3a3af89a079"
HASHES = {
    "model.onnx": "bbd7b466f6d58e646fdc2bd5fd67b2f5e93c0b687011bd4548c420f7bd46f0c5",
    "tokenizer.json": "da0e79933b9ed51798a3ae27893d3c5fa4a201126cef75586296df9b4d2c62a0",
}


def verify(path: Path, expected: str) -> None:
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise ValueError("Headroom model asset checksum mismatch; reinstall public assets")


def verify_assets(root: Path) -> None:
    cache = root / "headroom-assets/huggingface/hub/models--Qdrant--all-MiniLM-L6-v2-onnx"
    if (cache / "refs/main").read_text() != REVISION:
        raise ValueError("Headroom model ref differs from the pinned revision")
    for name, expected in HASHES.items():
        path = cache / "snapshots" / REVISION / name
        if not path.resolve().is_relative_to(cache.resolve()):
            raise ValueError("model asset points outside its private cache")
        verify(path, expected)
