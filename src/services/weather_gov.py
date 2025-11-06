import requests
from datetime import datetime
from typing import Tuple, Dict


class WeatherGovService:
    """Wraps the National Weather Service (weather.gov) API."""

    USER_AGENT = {"User-Agent": "weather-client/1.0"}

    # ------------------------------------------------------------------
    # 1️⃣ Resolve a lat/lon to the nearest observation station
    # ------------------------------------------------------------------
    @staticmethod
    def _point_metadata(lat: float, lon: float) -> dict:
        url = f"https://api.weather.gov/points/{lat},{lon}"
        resp = requests.get(url, headers=WeatherGovService.USER_AGENT)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _observation_station_url(point_meta: dict) -> str:
        return point_meta["properties"]["observationStations"]

    @staticmethod
    def _first_observation_station(stations_url: str) -> str:
        resp = requests.get(stations_url, headers=WeatherGovService.USER_AGENT)
        resp.raise_for_status()
        feats = resp.json()["features"]
        if not feats:
            raise ValueError("No observation stations found for this location.")
        return feats[0]["properties"]["stationIdentifier"]

    # ------------------------------------------------------------------
    # 2️⃣ Pull the latest observation payload
    # ------------------------------------------------------------------
    @staticmethod
    def _latest_observation(station_id: str) -> dict:
        url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
        resp = requests.get(url, headers=WeatherGovService.USER_AGENT)
        resp.raise_for_status()
        return resp.json()["properties"]

    # ------------------------------------------------------------------
    # 3️⃣ Pull the short‑term forecast (used for high/low predictions)
    # ------------------------------------------------------------------
    @staticmethod
    def _forecast_url(point_meta: dict) -> str:
        return point_meta["properties"]["forecast"]

    @staticmethod
    def _forecast_data(forecast_url: str) -> dict:
        resp = requests.get(forecast_url, headers=WeatherGovService.USER_AGENT)
        resp.raise_for_status()
        return resp.json()["properties"]["periods"]

    # ------------------------------------------------------------------
    # Public façade
    # ------------------------------------------------------------------
    def get_current_conditions(self, lat: float, lon: float, today: datetime.date) -> dict:
        """
        Returns a dictionary with:
        - station identifier
        - human readable city/state
        - distance (km) from the query point
        - timestamp of observation
        - temperature_F (current)
        - highlow tuple (high, low) in °F
        - wind speed (m/s)
        - text description
        """
        point_meta = self._point_metadata(lat, lon)

        # 1️⃣ Observation station
        stations_url = self._observation_station_url(point_meta)
        station_id = self._first_observation_station(stations_url)

        # 2️⃣ Latest observation
        obs = self._latest_observation(station_id)

        # 3️⃣ Forecast (high/low predictions)
        forecast_periods = self._forecast_data(self._forecast_url(point_meta))
        ## Subset to today's forecast periods
        forecast_periods_today = [
            entry for entry in forecast_periods
            if datetime.fromisoformat(entry['startTime']).date() == today
        ]
        temps = [entry['temperature'] for entry in forecast_periods_today]

        f_high = max(temps)
        f_low  = min(temps)

        # ----- Temperature conversions -----
        cur_f = (obs["temperature"]["value"] * 9 / 5) + 32 if obs["temperature"]["value"] is not None else None

        max24_f = (
            (obs["maxTemperatureLast24Hours"]["value"] * 9 / 5) + 32
            if obs["maxTemperatureLast24Hours"]["value"] is not None
            else cur_f
        )
        min24_f = (
            (obs["minTemperatureLast24Hours"]["value"] * 9 / 5) + 32
            if obs["minTemperatureLast24Hours"]["value"] is not None
            else cur_f
        )

        high = max(f_high, max24_f) if max24_f is not None else f_high
        low  = min(f_low,  min24_f) if min24_f is not None else f_low

        # ----- Assemble result -----
        city = point_meta["properties"]["relativeLocation"]["properties"]["city"]
        state = point_meta["properties"]["relativeLocation"]["properties"]["state"]
        distance_km = (
            point_meta["properties"]["relativeLocation"]["properties"]["distance"]["value"]
            / 1000
        )

        return {
            "station": station_id,
            "citystate": f"{city}, {state}",
            "distance": distance_km,
            "timestamp": obs["timestamp"],
            "temperature_F": cur_f,
            "highlow": (high, low),
            "wind_speed_mps": obs["windSpeed"]["value"],
            "text_description": obs["textDescription"],
        }