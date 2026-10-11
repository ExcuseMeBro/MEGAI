import time
from collections import OrderedDict


class TTLCache:
    """A fixed-capacity LRU cache with per-entry expiration."""

    def __init__(self, capacity, clock=time.monotonic):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self._capacity = capacity
        self._clock = clock
        self._entries = OrderedDict()

    def _purge_expired(self, now):
        expired = [key for key, (_, expiry) in self._entries.items() if now >= expiry]
        for key in expired:
            del self._entries[key]

    def put(self, key, value, ttl):
        if ttl <= 0:
            self._entries.pop(key, None)
            return
        now = self._clock()
        self._purge_expired(now)
        self._entries[key] = (value, now + ttl)
        self._entries.move_to_end(key)
        if len(self._entries) > self._capacity:
            self._entries.popitem(last=False)

    def get(self, key, default=None):
        entry = self._entries.get(key)
        if entry is None:
            return default
        value, expiry = entry
        if self._clock() >= expiry:
            del self._entries[key]
            return default
        self._entries.move_to_end(key)
        return value

    def delete(self, key):
        entry = self._entries.pop(key, None)
        return entry is not None and self._clock() < entry[1]

    def __len__(self):
        self._purge_expired(self._clock())
        return len(self._entries)
