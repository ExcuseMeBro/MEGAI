"""Durable Headroom adapters: atomic memory rows and capacity-bounded originals."""
from __future__ import annotations

import hashlib
import heapq
from pathlib import Path
import sqlite3
import time

CCR_BYTES = 64 * 1024 * 1024
CCR_ENTRIES = 256
TTL = 604800


class Originals:
    """Never evict a live original to make room; callers retain raw context instead."""

    def __init__(self, directory: Path):
        self.path = directory / "originals.db"
        if self.path.is_symlink():
            raise ValueError("symlinked originals database")
        with self.connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS originals (id TEXT PRIMARY KEY, content TEXT NOT NULL, expires REAL NOT NULL, size INTEGER NOT NULL)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def put(self, text: str) -> str | None:
        key = hashlib.sha256(text.encode()).hexdigest()[:24]
        size = len(text.encode())
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM originals WHERE expires < ?", (time.time(),))
            old = connection.execute("SELECT size FROM originals WHERE id=?", (key,)).fetchone()
            count, used = connection.execute("SELECT COUNT(*), COALESCE(SUM(size),0) FROM originals").fetchone()
            if count + (0 if old else 1) > CCR_ENTRIES or used - (old[0] if old else 0) + size > CCR_BYTES:
                return None
            connection.execute("INSERT OR REPLACE INTO originals VALUES (?,?,?,?)", (key, text, time.time() + TTL, size))
        self.path.chmod(0o600)
        return key

    def get(self, key: str) -> str | None:
        with self.connect() as connection:
            connection.execute("DELETE FROM originals WHERE expires < ?", (time.time(),))
            row = connection.execute("SELECT content FROM originals WHERE id=?", (key,)).fetchone()
        return row[0] if row else None


async def memory(directory: Path, action: str, text: str) -> dict:
    """Use Headroom's atomic SQLiteMemoryStore + local ONNX embedder.

    Text and embedding commit in one row, with content-derived idempotency keys.
    No independently committed vector/graph index can be orphaned by SIGKILL.
    Semantic recall ranks the stored embeddings; it does not need a second index.
    """
    import numpy as np
    from headroom.memory.adapters.sqlite import SQLiteMemoryStore
    from headroom.memory.adapters.embedders import OnnxLocalEmbedder
    from headroom.memory.models import Memory
    from headroom.memory.ports import MemoryFilter

    store = SQLiteMemoryStore(directory / "memory.db")
    key = hashlib.sha256(text.encode()).hexdigest()
    if action == "save" and await store.get(key) is not None:
        return {"id": key, "saved": True, "deduplicated": True}
    embedder = OnnxLocalEmbedder()
    try:
        vector = await embedder.embed(text)
        if vector.shape != (384,) or not np.isfinite(vector).all():
            raise ValueError("invalid local embedding")
        if action == "save":
            await store.save(Memory(id=key, content=text, user_id="megai", agent_id="pi", embedding=vector))
            return {"id": key, "saved": True, "deduplicated": False}
        rows = await store.query(MemoryFilter(user_id="megai"))
        best = heapq.nlargest(5, (
            (float(np.dot(vector, row.embedding)), row.id, row.content)
            for row in rows if row.embedding is not None
        ))
        return {"memories": [{"id": key, "content": content, "score": score}
                             for score, key, content in best]}
    finally:
        await embedder.close()
