"""Data store for an analysis session.

Gliaent's analysis code used to read and write `streamlit.session_state`
directly — including inside the MCP servers, which run as a headless
`python -m` child with no Streamlit script context. There, every
`st.session_state` access either raised or returned an unusable object, and
the surrounding `except Exception` turned that into a silent "analysis
failed". It is why the React/Electron shell could not drive the analysis
layer.

`DataStore` is the replacement: an explicit, injectable key-value store with
no framework dependency. The headless server gets an `InMemoryDataStore`; the
Streamlit app gets a `StreamlitDataStore` that delegates to
`st.session_state` so existing UI state keeps working; a test gets a plain
`InMemoryDataStore` with no setup.

Large objects (an AnnData, a protein matrix) stay in memory by design — this
is a per-session working set, not a cache. Persistence belongs to the project
directory and the run log, which record how to *recompute* a result rather
than storing every intermediate.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Iterator, List, Mapping, Optional, Protocol, runtime_checkable


@runtime_checkable
class DataStore(Protocol):
    """The interface analysis code depends on.

    Deliberately narrow: get, set, delete, contains, keys. Anything wider
    tempts callers back toward framework-specific behaviour.
    """

    def get(self, key: str, default: Any = None) -> Any: ...

    def set(self, key: str, value: Any) -> None: ...

    def delete(self, key: str) -> None: ...

    def has(self, key: str) -> bool: ...

    def keys(self) -> List[str]: ...


class InMemoryDataStore:
    """Thread-safe in-process store.

    The default for headless servers and tests. Uses an RLock because the MCP
    server runs a thread-pool executor alongside its event loop, so concurrent
    access is real rather than theoretical.
    """

    def __init__(self, initial: Optional[Mapping[str, Any]] = None) -> None:
        self._data: Dict[str, Any] = dict(initial or {})
        self._lock = threading.RLock()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._data

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._data)

    # Mapping-style sugar, so this can stand in for a dict in existing code.
    def __getitem__(self, key: str) -> Any:
        with self._lock:
            return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        with self._lock:
            del self._data[key]

    def __contains__(self, key: str) -> bool:
        return self.has(key)

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class StreamlitDataStore:
    """Adapter over `streamlit.session_state`.

    Lets the Streamlit UI keep its existing state while the analysis layer
    below it talks only to `DataStore`. Importing this class does not import
    Streamlit; the import happens on first use, so the module stays safe to
    load in a headless process.

    Raises:
        RuntimeError: On first access if Streamlit is not installed or there
            is no script run context. This is deliberately loud: the silent
            version of this failure is the bug this module exists to fix.
        """

    def __init__(self) -> None:
        self._state: Any = None

    @property
    def state(self) -> Any:
        if self._state is None:
            try:
                import streamlit as st

                # Touch it, so a missing run context fails here rather than
                # halfway through an analysis.
                _ = len(st.session_state)
                self._state = st.session_state
            except Exception as exc:  # pragma: no cover - needs Streamlit
                raise RuntimeError(
                    "StreamlitDataStore requires a live Streamlit script run "
                    "context. In a headless process (the MCP server child, a "
                    "test, a notebook) use InMemoryDataStore instead."
                ) from exc
        return self._state

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.state[key] = value

    def delete(self, key: str) -> None:
        if key in self.state:
            del self.state[key]

    def has(self, key: str) -> bool:
        return key in self.state

    def keys(self) -> List[str]:
        return list(self.state.keys())


class MissingDataError(KeyError):
    """Raised when analysis is asked to run without its input.

    A distinct type so API and UI layers can map it to "you have not loaded
    data yet" rather than a 500.
    """


def require(store: DataStore, key: str, what: str = "data") -> Any:
    """Fetch a required value or raise with an actionable message.

    Use instead of `store.get(key)` followed by a truthiness check, which is
    how the old code turned missing input into a confusing downstream
    `AttributeError` on `None`.

    Raises:
        MissingDataError: If `key` is absent.
    """
    if not store.has(key):
        available = ", ".join(sorted(store.keys())) or "nothing loaded"
        raise MissingDataError(
            f"{what} not available: no {key!r} in this session "
            f"(available: {available})"
        )
    return store.get(key)
