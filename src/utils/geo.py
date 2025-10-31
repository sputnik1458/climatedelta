import math

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great‑circle distance in kilometres between two lat/lon pairs."""
    R = 6371.0
    φ1, φ2 = map(math.radians, (lat1, lat2))
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)

    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def c_to_f(celsius: float) -> float:
    """Convert Celsius → Fahrenheit."""
    return celsius * 9 / 5 + 32