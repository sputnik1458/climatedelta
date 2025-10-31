import sys
from datetime import datetime, timezone

from .config import Colours
from .services.zip_lookup import ZipLookupService
from .services.noaa_station import NOAAStationService
from .services.weather_gov import WeatherGovService
from .utils.geo import haversine

def colourize(delta: float, positive_color: str, negative_color: str) -> str:
    """Helper to wrap a temperature delta with the proper ANSI colour."""
    if delta > 0:
        return f"{positive_color}{delta:.1f}°F warmer{Colours.RESET}"
    elif delta < 0:
        return f"{negative_color}{-delta:.1f}°F cooler{Colours.RESET}"
    else:
        return f"{Colours.GREEN}no change{Colours.RESET}"


def main() -> None:
    zip_service = ZipLookupService()
    station_service = NOAAStationService()
    weather_service = WeatherGovService()

    # ------------------------------------------------------------------
    # 1️⃣ Gather user location (ZIP or “City, STATE”)
    # ------------------------------------------------------------------
    loc = input("Enter ZIP or (City, STATE): ").strip()
    if len(loc) == 5 and loc.isdigit():
        zip_code = loc
    else:
        print(f"Resolving '{loc}' to a ZIP…")
        zip_code = zip_service.city_state_to_zip(loc)
        if not zip_code:
            sys.exit("Could not resolve city/state to a ZIP code.")
        print(f"Resolved to ZIP {zip_code}")

    # ------------------------------------------------------------------
    # 2️⃣ Convert ZIP → lat/lon
    # ------------------------------------------------------------------
    lat, lon = zip_service.zip_to_latlon(zip_code)
    print(f"Coordinates: {lat:.4f}, {lon:.4f}")

    # ------------------------------------------------------------------
    # 3️⃣ Find the best NOAA climate station (with normals)
    # ------------------------------------------------------------------
    station_id, station_name, s_lat, s_lon = station_service.get_closest_station_with_normals(
        lat, lon
    )
    dist_km = haversine(lat, lon, s_lat, s_lon)
    print(
        f"\nNearest climate station ({dist_km:.1f} km): {station_name} ({station_id})"
    )

    # ------------------------------------------------------------------
    # 4️⃣ Load historical normals for today
    # ------------------------------------------------------------------
    normals = station_service.get_normals_for_today(station_id)
    today = datetime.now(timezone.utc).date()
    print(
        f"\t1981‑2010 normals for {today}: "
        f"High {normals['high_avg']:.1f}°F, Low {normals['low_avg']:.1f}°F "
        f"(1σ range: {normals['high_sd']:.1f}–{normals['low_sd']:.1f}°F)"
    )

    # ------------------------------------------------------------------
    # 5️⃣ Pull current observations from weather.gov
    # ------------------------------------------------------------------
    current = weather_service.get_current_conditions(lat, lon)
    print(
        f"Nearest weather station ({current['distance']:.1f} km): "
        f"{current['citystate']} ({current['station']})"
    )
    print(
        f"\tCurrent Temperature: {current['temperature_F']:.1f}°F "
        f"(High: {current['highlow'][0]:.1f}°F, Low: {current['highlow'][1]:.1f}°F)"
    )

    # ------------------------------------------------------------------
    # 6️⃣ How much hotter / colder than the normals?
    # ------------------------------------------------------------------
    delta_high = current["highlow"][0] - normals["high_avg"]
    delta_low  = current["highlow"][1] - normals["low_avg"]

    print(
        f"\nToday's high is {colourize(delta_high, Colours.RED, Colours.CYAN)} "
        f"and today's low is {colourize(delta_low, Colours.RED, Colours.CYAN)} "
        f"versus the 1981‑2010 climate."
    )

    # ------------------------------------------------------------------
    # 7️⃣ Quick sanity check: are we within 1 σ of the historic mean?
    # ------------------------------------------------------------------
    high_in_range = current["highlow"][0] <= normals["high_sd"]
    low_in_range  = current["highlow"][1] >= normals["low_sd"]

    if high_in_range and low_in_range:
        msg = f"{Colours.GREEN}Both today's high and low sit within the historical average.{Colours.RESET}"
    elif high_in_range:
        msg = f"{Colours.CYAN}High is within range, low is below the 1σ lower bound.{Colours.RESET}"
    elif low_in_range:
        msg = f"{Colours.RED}Low is within range, high is above the 1σ upper bound.{Colours.RESET}"
    else:
        msg = f"{Colours.YELLOW}Both high and low lie outside 1σ of the historic average.{Colours.RESET}"
    print(msg)


if __name__ == "__main__":
    main()