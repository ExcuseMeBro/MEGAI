#!/usr/bin/env python3
"""Install-only public tokenizer/model downloads. Never reads agent context/auth."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pi-skill/headroom"))
from bridge import private_directory  # noqa: E402
from assets import HASHES, REPOSITORY, REVISION, verify  # noqa: E402

os.umask(0o077)
root = Path(os.environ.get("MEGAI_HOME", Path.home() / ".megai"))
assets = private_directory(root / "headroom-assets")
cache = private_directory(assets / "tiktoken")
for name, digest in (
    ("o200k_base", "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"),
    ("cl100k_base", "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"),
):
    url = f"https://openaipublic.blob.core.windows.net/encodings/{name}.tiktoken"
    destination = cache / hashlib.sha1(url.encode()).hexdigest()
    if destination.is_symlink():
        raise SystemExit("symlinked tokenizer cache")
    if not destination.exists() or hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
        temporary = destination.with_suffix(".download")
        if temporary.exists() or temporary.is_symlink():
            raise SystemExit("unfinished tokenizer download preserved; reconcile manually")
        try:
            subprocess.run(["curl", "--fail", "--silent", "--show-error", "--proto", "=https",
                            "--connect-timeout", "10", "--max-time", "120", url, "-o", str(temporary)], check=True)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != digest:
                raise SystemExit("tokenizer checksum mismatch")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)

os.environ.update({
    "HF_HOME": str(private_directory(assets / "huggingface")),
    "HF_ENDPOINT": "https://huggingface.co", "HF_HUB_OFFLINE": "0",
    "HF_HUB_DISABLE_TELEMETRY": "1", "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1",
    "HF_HUB_DOWNLOAD_TIMEOUT": "120", "HF_HUB_DISABLE_XET": "1",
})
from huggingface_hub import hf_hub_download  # noqa: E402

for filename, expected in HASHES.items():
    downloaded = Path(hf_hub_download(REPOSITORY, filename, revision=REVISION, token=False))
    verify(downloaded, expected)
# Headroom's ONNX adapter requests the default ref. Pin that ref in this private,
# dedicated cache, then runtime HF_HUB_OFFLINE prevents moving it on startup.
refs = private_directory(assets / "huggingface/hub/models--Qdrant--all-MiniLM-L6-v2-onnx/refs")
(refs / "main").write_text(REVISION)
print("Headroom public assets prepared; runtime uses offline inference only")
