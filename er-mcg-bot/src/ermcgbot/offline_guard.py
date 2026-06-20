"""Network egress guard — provable 'runs off the network' enforcement.

Security reviewers don't want to be *told* the bot makes no outbound internet
calls; they want it demonstrated. This module installs a process-wide block on
outbound socket connections. With it active, any attempt to phone home raises
`NetworkBlocked` instead of succeeding — so you can run the whole screening
pipeline with egress disabled and show it still works end to end.

Usage:
    from ermcgbot.offline_guard import activate
    activate()                      # block ALL outbound connections
    activate(allow={("10.0.0.5", 443)})  # internal EHR host only, no internet

In a real internal-only deployment the OS/network firewall is the primary
control; this guard is a defense-in-depth backstop and a verification tool.
"""
from __future__ import annotations

import socket
from typing import Optional, Set, Tuple

_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex
_active = False
_allow: Set[Tuple[str, Optional[int]]] = set()


class NetworkBlocked(OSError):
    """Raised when an outbound connection is attempted while the guard is on."""


def _allowed(address) -> bool:
    if not isinstance(address, tuple):
        return address in _allow  # AF_UNIX path, etc.
    host = address[0]
    port = address[1] if len(address) > 1 else None
    return (host, port) in _allow or (host, None) in _allow or host in _allow


def _guard_connect(self, address):
    if _active and not _allowed(address):
        raise NetworkBlocked(
            f"Outbound connection to {address!r} blocked: offline guard is "
            f"active. This process is configured to make no network egress."
        )
    return _original_connect(self, address)


def _guard_connect_ex(self, address):
    if _active and not _allowed(address):
        raise NetworkBlocked(
            f"Outbound connection to {address!r} blocked: offline guard active."
        )
    return _original_connect_ex(self, address)


def activate(allow: Optional[Set[Tuple[str, Optional[int]]]] = None) -> None:
    """Block outbound connections, except to addresses in `allow`."""
    global _active, _allow
    _allow = set(allow or set())
    _active = True
    socket.socket.connect = _guard_connect  # type: ignore[assignment]
    socket.socket.connect_ex = _guard_connect_ex  # type: ignore[assignment]


def deactivate() -> None:
    """Restore normal socket behavior (used by tests)."""
    global _active
    _active = False
    socket.socket.connect = _original_connect  # type: ignore[assignment]
    socket.socket.connect_ex = _original_connect_ex  # type: ignore[assignment]


def is_active() -> bool:
    return _active
