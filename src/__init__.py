"""
weather_app package – a tiny CLI tool that compares today’s weather
to historic climate normals.

Public entry points
-------------------
* `weather_app.main` – the command‑line driver (`python -m weather_app.main`)
* Service classes:
    - `ZipLookupService`
    - `NOAAStationService`
    - `WeatherGovService`
* Utility helpers:
    - `haversine`
    - `c_to_f`
* Colour constants via `weather_app.Colours`

Having these symbols available at the package root keeps the import
experience ergonomic:

    >>> from weather_app import ZipLookupService, haversine, Colours
"""

# ----------------------------------------------------------------------
# Version information – keep it in a single place
# ----------------------------------------------------------------------
__all__ = [
    "VERSION",
    "ColouredText",
    # Services
    "ZipLookupService",
    "NOAAStationService",
    "WeatherGovService",
    # Utilities
    "haversine",
    "c_to_f",
]

# Semantic version of the library (you can bump this when you publish a new release)
VERSION = "0.1.0"


# ----------------------------------------------------------------------
# Re‑export colour constants (they live in `weather_app.config`)
# ----------------------------------------------------------------------
from .config import Colours as ColouredText  # noqa: F401


# ----------------------------------------------------------------------
# Re‑export the three service classes (they are defined in sub‑packages)
# ----------------------------------------------------------------------
from .services import (  # noqa: F401
    ZipLookupService,
    NOAAStationService,
    WeatherGovService,
)

# ----------------------------------------------------------------------
# Re‑export the geometry helpers from the utils package
# ----------------------------------------------------------------------
from .utils import haversine, c_to_f  # noqa: F401