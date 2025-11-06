import os
from datetime import datetime, timezone

from flask import Flask, render_template, request, redirect, url_for, flash

# Import the OOP services you already wrote
from src.services import (
    ZipLookupService,
    NOAAStationService,
    WeatherGovService,
)
from src.utils import haversine
from src.config import Colours

app = Flask(__name__)
# Needed for flashing messages (error handling)
app.secret_key = os.urandom(24)


def colourize(delta: float) -> str:
    """Return a coloured HTML snippet for a temperature delta."""
    if delta > 0:
        return f'<span style="color:{Colours.RED}">{delta:.1f}°F warmer</span>'
    elif delta < 0:
        return f'<span style="color:{Colours.CYAN}">{-delta:.1f}°F cooler</span>'
    else:
        return '<span style="color:green">no change</span>'


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        location = request.form.get("location", "").strip()
        if not location:
            flash("Please enter a ZIP code or a city/state.", "error")
            return redirect(url_for("index"))

        # ------------------------------------------------------------------
        # Resolve the location → ZIP → lat/lon
        # ------------------------------------------------------------------
        zip_service = ZipLookupService()
        if len(location) == 5 and location.isdigit():
            zip_code = location
        else:
            app.logger.info("Resolving zip for city/state...")
            zip_code = zip_service.city_state_to_zip(location)
            if not zip_code:
                flash(f"Could not resolve '{location}' to a ZIP code.", "error")
                return redirect(url_for("index"))

        try:
            app.logger.info("Resolving lat/long for zip...")
            lat, lon = zip_service.zip_to_latlon(zip_code)
        except Exception as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))

        # ------------------------------------------------------------------
        # Pull climate normals (NOAA) and current conditions (weather.gov)
        # ------------------------------------------------------------------
        station_svc = NOAAStationService()
        weather_svc = WeatherGovService()
        today = datetime.now(timezone.utc).date()
        
        try:
            app.logger.info("Getting valid NOAA station...")
            station_id, station_name, s_lat, s_lon = station_svc.get_closest_station_with_normals(
                lat, lon
            )
            dist_to_station = haversine(lat, lon, s_lat, s_lon)

            app.logger.info("Getting climate normals...")
            normals = station_svc.get_normals_for_today(station_id)
            app.logger.info("Getting current conditions...")
            current = weather_svc.get_current_conditions(lat, lon, today)

        except Exception as exc:
            flash(f"Data retrieval error: {exc}", "error")
            return redirect(url_for("index"))

        # ------------------------------------------------------------------
        # Compute deltas (how much hotter/colder than normals)
        # ------------------------------------------------------------------
        delta_high = current["highlow"][0] - normals["high_avg"]
        delta_low = current["highlow"][1] - normals["low_avg"]

        # ------------------------------------------------------------------
        # Render the result template
        # ------------------------------------------------------------------
        return render_template(
            "result.html",
            location_input=location,
            zip_code=zip_code,
            lat=lat,
            lon=lon,
            station_name=station_name,
            station_id=station_id,
            station_dist=dist_to_station,
            normals=normals,
            today=today,
            current=current,
            delta_high_html=colourize(delta_high),
            delta_low_html=colourize(delta_low),
        )

    # GET request – just show the empty form
    return render_template("index.html")


if __name__ == "__main__":
    # For development only – use a proper WSGI server in production
    app.run(debug=True, host="0.0.0.0", port=5000)