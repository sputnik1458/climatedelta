from numpy import rint
import requests
from datetime import datetime, timezone
import math
import pandas as pd

def get_lat_lon_from_zip(zip_code):
    """Get latitude and longitude from a ZIP code using Zippopotam.us."""
    url = f"http://api.zippopotam.us/us/{zip_code}"
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError("Invalid ZIP code or unable to retrieve location data.")
    
    data = response.json()
    lat = float(data['places'][0]['latitude'])
    lon = float(data['places'][0]['longitude'])
    return lat, lon

def haversine(lat1, lon1, lat2, lon2):
    """Compute distance in kilometers between two lat/lon points."""
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_nearest_station(lat, lon, token):
    """Get nearest NOAA station (NORMAL_DLY dataset) based on actual distance."""
    url = "https://www.ncei.noaa.gov/cdo-web/api/v2/stations"
    params = {
        "datasetid": "NORMAL_DLY",
        "extent": f"{lat-1},{lon-1},{lat+1},{lon+1}",  # 2° box around point
        "limit": 100,
    }
    headers = {"token": token}
    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()
    stations = resp.json().get("results", [])
    if not stations:
        raise ValueError("No climate stations found near this location.")

    # Compute distances and choose closest
    closest = min(
        stations,
        key=lambda s: haversine(
            lat, lon, s["latitude"], s["longitude"]
        )
    )
    return closest["id"], closest["name"], closest["latitude"], closest["longitude"]

# --------------------------------------------------------------
# Nearest station that has the daily‑normals CSV
# --------------------------------------------------------------
def get_closest_station_with_normals(lat, lon, token):
    """
    Query NOAA for stations in a ~2° box, then return the closest one
    that yields a usable CSV containing the DLY‑TMAX‑NORMAL column.
    """
    base_url = "https://www.ncei.noaa.gov/cdo-web/api/v2/stations"
    params = {
        "datasetid": "NORMAL_DLY",
        "extent": f"{lat-1},{lon-1},{lat+1},{lon+1}",
        "limit": 100,
    }
    headers = {"token": token}
    resp = requests.get(base_url, params=params, headers=headers)
    resp.raise_for_status()
    stations = resp.json().get("results", [])

    if not stations:
        raise ValueError("No climate stations found near this location.")

    # Sort stations by straight‑line distance first
    stations.sort(key=lambda s: haversine(lat, lon,
                                          s["latitude"], s["longitude"]))

    # Try each station until we find one with a usable CSV
    for s in stations:
        station_id = s["id"]
        # Build the CSV URL – the part after the colon is the station code
        csv_url = (
            "https://www.ncei.noaa.gov/data/normals-daily/1981-2010/access/"
            + station_id.split(":")[1] + ".csv"
        )
        try:
            df = pd.read_csv(csv_url, nrows=1)   # just peek at header
            if "DLY-TMAX-NORMAL" in df.columns:
                # We have a good station – fetch the full CSV later
                return (
                    station_id,
                    s["name"],
                    s["latitude"],
                    s["longitude"],
                )
        except Exception:
            # Either the CSV is missing or malformed – move on
            continue

    raise ValueError(
        "No nearby station provides DLY‑TMAX‑NORMAL data."
    )

def get_normals_for_today(station_id, token, today):
    """Fetch daily normals for today from NOAA for the given station."""
    df = pd.read_csv("https://www.ncei.noaa.gov/data/normals-daily/1981-2010/access/" + station_id.split(':')[1] + ".csv")

    result = df[df["DATE"]==f"{datetime.today().month}-{datetime.today().day}"]

    high_avg = result[['DLY-TMAX-NORMAL']].iloc[0].item()
    high_sd = high_avg + result[['DLY-TMAX-STDDEV']].iloc[0].item()
    low_avg = result[['DLY-TMIN-NORMAL']].iloc[0].item()
    low_sd = low_avg - result[['DLY-TMIN-STDDEV']].iloc[0].item()

    # Select specific columns
    # Divide by 10 to get deg F
    return({"high_avg": high_avg/10,
            "high_sd": high_sd/10,
            "low_avg": low_avg/10,
            "low_sd": low_sd/10})

def get_current_temp(lat,lon):
    """"Fetch current weather data from weather.gov given lat/lon."""
    headers = {"User-Agent": "weather-client/1.1"}
    
    # Step 1: Get metadata about the location
    points_url = f"https://api.weather.gov/points/{lat},{lon}"
    points_response = requests.get(points_url, headers={"User-Agent": "weather-client/1.0"})
    points_response.raise_for_status()
    points_data = points_response.json()
    
    # Step 2: Get the observation station URL
    observation_stations_url = points_data['properties']['observationStations']
    stations_response = requests.get(observation_stations_url, headers={"User-Agent": "weather-client/1.0"})
    stations_response.raise_for_status()
    stations_data = stations_response.json()
    
    if not stations_data['features']:
        raise ValueError("No observation stations found for this location.")
    
    # Use the first station
    station_id = stations_data['features'][0]['properties']['stationIdentifier']
    
    # Step 3: Get latest observation data
    observation_url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
    observation_response = requests.get(observation_url, headers={"User-Agent": "weather-client/1.0"})
    observation_response.raise_for_status()
    observation_data = observation_response.json()
    
    props = observation_data['properties']

    # Step 4: Get forecast (for highs/lows)
    forecast_url = points_data['properties']['forecast']
    forecast_response = requests.get(forecast_url, headers=headers)
    forecast_response.raise_for_status()
    forecast_data = forecast_response.json()
    
    # Extract today's forcasted high and low
    
    f_high = forecast_data['properties']['periods'][0]['temperature']
    f_low = forecast_data['properties']['periods'][1]['temperature']

    # Set true high/low
    current_temp_f = (props['temperature']['value'] * 9/5) + 32
    max_temp24_f = (props['maxTemperatureLast24Hours']['value'] * 9/5) + 32 if props['maxTemperatureLast24Hours']['value'] is not None else current_temp_f
    min_temp24_f = (props['minTemperatureLast24Hours']['value'] * 9/5) + 32 if props['minTemperatureLast24Hours']['value'] is not None else current_temp_f
    high = f_high if f_high > max_temp24_f else max_temp24_f
    low = f_low if f_low < min_temp24_f else min_temp24_f

    return {
        "station": station_id,
        "citystate": points_data['properties']['relativeLocation']['properties']['city'] + ", " + points_data['properties']['relativeLocation']['properties']['state'],
        "distance": points_data['properties']['relativeLocation']['properties']['distance']['value'] / 1000, 
        "timestamp": props['timestamp'],
        "temperature_F": current_temp_f,
        "highlow": (high, low),
        "wind_speed_mps": props['windSpeed']['value'],
        "text_description": props['textDescription']
    }

# Usage in your main script
if __name__ == "__main__":
    today = datetime.now(timezone.utc).date()
    zip_code = input("Enter ZIP: ").strip()
    token = "hnVrhBmeSzXXPyMASciXwzgnsPIjGLIC"
    lat, lon = get_lat_lon_from_zip(zip_code)
    print(f"Coordinates: {lat:.4f}, {lon:.4f}")
    # station_id, station_name, s_lat, s_lon = get_nearest_station(lat, lon, token)
    station_id, station_name, s_lat, s_lon = get_closest_station_with_normals(lat, lon, token)
    dist_km = haversine(lat, lon, s_lat, s_lon)

    print(f"\nNearest climate station ({dist_km:.1f} km): {station_name} ({station_id})")
    normals = get_normals_for_today(station_id, token, today)
    print(f"\t1981-2010 normals for {today}: High: {normals['high_avg']}°F, Low: {normals['low_avg']}°F (1SD range: {normals['high_sd']}-{normals['low_sd']}°F)")

    current_conditions = get_current_temp(lat,lon)
    print(f"Nearest weather station ({current_conditions['distance']:.1f} km): {current_conditions['citystate']} ({current_conditions['station']})")
    print(f"\tCurrent Temperature: {current_conditions['temperature_F']:.1f}°F (High: {current_conditions['highlow'][0]}°F, Low: {current_conditions['highlow'][1]}°F)")

    delta_high = current_conditions['highlow'][0] - normals['high_avg']
    delta_high_str = f"{delta_high:.1f}°F warmer" if delta_high > 0 else f"{-delta_high:.1f}°F cooler"
    delta_low = current_conditions['highlow'][1] - normals['low_avg']
    delta_low_str = f"{delta_low:.1f}°F warmer" if delta_low > 0 else f"{-delta_low:.1f}°F cooler"
    print(f"\nToday's high is {delta_high_str} and today's low is {delta_low_str} versus the 1981-2010 average.")

    isHighInRange = normals['high_avg'] < normals['high_sd']
    isLowInRange = normals['low_avg'] > normals['low_sd']

    if isHighInRange and isLowInRange:
        print("Both today's high and low are within the historical average.")
    elif isHighInRange:
        print("Today's high is within the historical average, but today's low is below that range.")
    elif isLowInRange:
        print("Today's low is within the historical average, but today's high is above that range.")
    else:
        print("Both today's high and low are outside 1 standard deviation of the historical average.")
