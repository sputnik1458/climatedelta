import requests

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


def get_weather_from_weather_gov(lat, lon):
    """Fetch current weather data from weather.gov given lat/lon."""
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
    return {
        "station": station_id,
        "timestamp": props['timestamp'],
        "temperature_C": props['temperature']['value'],
        "wind_speed_mps": props['windSpeed']['value'],
        "text_description": props['textDescription']
    }


if __name__ == "__main__":
    zip_code = input("Enter a US ZIP code: ").strip()
    try:
        lat, lon = get_lat_lon_from_zip(zip_code)
        weather = get_weather_from_weather_gov(lat, lon)
        print(f"\nCurrent weather near ZIP {zip_code}:")
        print(f"Station: {weather['station']}")
        print(f"Time: {weather['timestamp']}")
        print(f"Conditions: {weather['text_description']}")
        print(f"Temperature: {weather['temperature_C']} °C")
        print(f"Wind Speed: {weather['wind_speed_mps']} m/s")
    except Exception as e:
        print("Error:", e)