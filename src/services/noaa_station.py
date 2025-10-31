import requests
import pandas as pd
from typing import Tuple
from ..utils.geo import haversine
from ..config import NOAA_TOKEN


class NOAAStationService:
    """Find the nearest NOAA climate station that actually provides daily normals."""

    BASE_URL = "https://www.ncei.noaa.gov/cdo-web/api/v2/stations"
    NORMALS_CSV_ROOT = (
        "https://www.ncei.noaa.gov/data/normals-daily/1981-2010/access/"
    )

    def __init__(self, token: str = NOAA_TOKEN):
        self.token = token

    # ------------------------------------------------------------------
    # 1️⃣ Find the closest station that has a usable CSV
    # ------------------------------------------------------------------
    def get_closest_station_with_normals(
        self, lat: float, lon: float
    ) -> Tuple[str, str, float, float]:
        """
        Returns (station_id, name, latitude, longitude) for the nearest
        station whose CSV contains the DLY‑TMAX‑NORMAL column.
        """
        params = {
            "datasetid": "NORMAL_DLY",
            "extent": f"{lat-1},{lon-1},{lat+1},{lon+1}",
            "limit": 100,
        }
        headers = {"token": self.token}
        resp = requests.get(self.BASE_URL, params=params, headers=headers)
        resp.raise_for_status()
        stations = resp.json().get("results", [])
        if not stations:
            raise ValueError("No climate stations found near this location.")

        # Sort by straight‑line distance first
        stations.sort(
            key=lambda s: haversine(lat, lon, s["latitude"], s["longitude"])
        )

        # Scan for a station that actually hosts the CSV we need
        for s in stations:
            station_id = s["id"]
            csv_url = (
                self.NORMALS_CSV_ROOT + station_id.split(":")[1] + ".csv"
            )
            try:
                # Peek at the header only – cheap check
                df = pd.read_csv(csv_url, nrows=1)
                if "DLY-TMAX-NORMAL" in df.columns:
                    return (
                        station_id,
                        s["name"],
                        s["latitude"],
                        s["longitude"],
                    )
            except Exception:
                # Missing or malformed CSV – keep looking
                continue

        raise ValueError(
            "No nearby station provides DLY‑TMAX‑NORMAL data."
        )

    # ------------------------------------------------------------------
    # 2️⃣ Load today’s normals from the chosen station
    # ------------------------------------------------------------------
    def get_normals_for_today(self, station_id: str) -> dict:
        """
        Returns a dict with high/low averages and ±1 σ values (°F).
        """
        csv_url = (
            self.NORMALS_CSV_ROOT + station_id.split(":")[1] + ".csv"
        )
        df = pd.read_csv(csv_url)

        today_md = pd.Timestamp.now().strftime("%m-%d")
        row = df[df["DATE"] == today_md].iloc[0]

        # Values in the CSV are tenths of °F
        high_avg = row["DLY-TMAX-NORMAL"] / 10
        high_sd  = (row["DLY-TMAX-NORMAL"] + row["DLY-TMAX-STDDEV"]) / 10
        low_avg  = row["DLY-TMIN-NORMAL"] / 10
        low_sd   = (row["DLY-TMIN-NORMAL"] - row["DLY-TMIN-STDDEV"]) / 10

        # Convert to Fahrenheit
        from ..utils.geo import c_to_f

        return {
            "high_avg": high_avg,
            "high_sd":  high_sd,
            "low_avg":  low_avg,
            "low_sd":   low_sd,
        }