"""
utils package – small, pure‑function helpers.

We expose the geometry helpers that are used throughout the app.
"""

# Re‑export the helpers for a clean import path
from .geo import haversine, c_to_f   # noqa: F401

__all__ = [
    "haversine",
    "c_to_f",
]