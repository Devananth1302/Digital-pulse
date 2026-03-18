"""Utility helpers for Digital Pulse."""

import hashlib
from datetime import datetime, timezone


def generate_id(text: str, prefix: str = "") -> str:
    """Generate a short deterministic ID from text."""
    raw = f"{prefix}:{text}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """Safe division with fallback."""
    return a / b if b != 0 else default


def truncate(text: str, max_len: int = 200) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def format_number(n: float) -> str:
    """Human-readable number formatting."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))
