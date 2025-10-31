import requests
from typing import Tuple, Optional


class ZipLookupService:
    """Resolve ZIP ↔ lat/lon and City,State → ZIP."""

    @staticmethod
    def zip_to_latlon(zip_code: str) -> Tuple[float, float]:
        """Return (lat, lon) for a US ZIP using Zippopotam."""
        url = f"http://api.zippopotam.us/us/{zip_code}"
        resp = requests.get(url)
        if resp.status_code != 200:
            raise ValueError("Invalid ZIP code or service unavailable.")
        data = resp.json()["places"][0]
        return float(data["latitude"]), float(data["longitude"])

    @staticmethod
    def city_state_to_zip(city_state: str) -> Optional[str]:
        """
        Convert a “City, State” string to a ZIP using Zippopotam.
        Returns the first ZIP found or None.
        """
        try:
            city, state = [x.strip() for x in city_state.split(",")]
            url = f"http://api.zippopotam.us/us/{state}/{city}"
            resp = requests.get(url)
            if resp.status_code == 200:
                return resp.json()["places"][0]["post code"]
        except Exception as exc:
            print(f"Error converting city/state → ZIP: {exc}")
        return None