"""Bounded defensive cache keyed only by canonical case signatures."""

from __future__ import annotations

import copy
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock

import numpy as np

from .errors import PanelSolverError
from .signatures import CaseSignature


class ResultCacheError(PanelSolverError, ValueError):
    """Result-cache configuration or copy operation failed."""


@dataclass(frozen=True, slots=True)
class ResultCacheStats:
    """Atomic statistics for one result-cache instance."""

    entries: int
    hits: int
    misses: int
    evictions: int


class ResultCache[T]:
    """Thread-safe LRU cache that copies values on insertion and lookup."""

    def __init__(self, max_entries: int = 1) -> None:
        if isinstance(max_entries, (bool, np.bool_)) or not isinstance(
            max_entries, (int, np.integer)
        ):
            raise ResultCacheError("max_entries must be an integer >= 0.")
        if int(max_entries) < 0:
            raise ResultCacheError("max_entries must be an integer >= 0.")
        self._max_entries = int(max_entries)
        self._entries: OrderedDict[str, T] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._lock = Lock()

    @property
    def max_entries(self) -> int:
        return self._max_entries

    def _copy(self, value: T) -> T:
        try:
            return copy.deepcopy(value)
        except Exception as exc:
            raise ResultCacheError(f"Unable to copy cached result: {exc}") from exc

    def get(self, signature: CaseSignature) -> T | None:
        """Return a defensive copy, or ``None`` after recording a miss."""
        if not isinstance(signature, CaseSignature):
            raise TypeError("signature must be a CaseSignature instance")
        with self._lock:
            if self._max_entries == 0:
                self._misses += 1
                return None
            if signature.digest not in self._entries:
                self._misses += 1
                return None
            value = self._entries[signature.digest]
            self._hits += 1
            self._entries.move_to_end(signature.digest)
            return self._copy(value)

    def put(self, signature: CaseSignature, value: T) -> None:
        """Store a defensive copy unless this cache is disabled."""
        if not isinstance(signature, CaseSignature):
            raise TypeError("signature must be a CaseSignature instance")
        if self._max_entries == 0:
            return
        copied = self._copy(value)
        with self._lock:
            self._entries[signature.digest] = copied
            self._entries.move_to_end(signature.digest)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
                self._evictions += 1

    def clear(self, *, reset_stats: bool = True) -> None:
        """Clear entries and optionally hit/miss/eviction counters."""
        with self._lock:
            self._entries.clear()
            if reset_stats:
                self._hits = 0
                self._misses = 0
                self._evictions = 0

    def stats(self) -> ResultCacheStats:
        """Return an atomic statistics snapshot."""
        with self._lock:
            return ResultCacheStats(
                entries=len(self._entries),
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
            )


__all__ = ("ResultCache", "ResultCacheError", "ResultCacheStats")
