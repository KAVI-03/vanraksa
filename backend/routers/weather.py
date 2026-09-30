"""Weather router — sync wrapper."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import httpx, uuid
from datetime import datetime, timedelta
from config import settings

router = APIRouter(prefix="/weather", tags=["weather"])

CACHE_TTL_MINUTES = 15

def _location_key(lat, lng): return f"lat:{round(lat,2)}_lng:{round(lng,2)}"
def _deg_to_compass(deg):
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[round(deg/22.5)%16]


# ── Weather for the 4 default trail locations (used by the tourist home ticker) ──
TRAIL_LOCATIONS = [
    {"id": "kasauli", "city": "Kasauli", "lat": 30.8950, "lng": 76.9380},
    {"id": "dzukou", "city": "Dzukou Valley", "lat": 25.5450, "lng": 94.1350},
    {"id": "goechala", "city": "Goechala", "lat": 27.3710, "lng": 88.2230},
    {"id": "david-scott", "city": "David Scott Trail", "lat": 25.4520, "lng": 91.7580},
]
_WMO = {0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Rime fog",
        51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
        71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains", 80: "Rain showers",
        81: "Heavy showers", 82: "Violent showers", 85: "Snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm with hail"}
_list_cache = {"at": None, "data": []}


def _fetch_trail_weather():
    out = []
    for loc in TRAIL_LOCATIONS:
        try:
            r = httpx.get(
                "https://api.open-meteo.com/v1/forecast",
                params={"latitude": loc["lat"], "longitude": loc["lng"],
                        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"},
                timeout=6,
            )
            r.raise_for_status()
            c = r.json().get("current", {})
            code = int(c.get("weather_code", 0))
            out.append({
                "id": loc["id"], "city": loc["city"], "lat": loc["lat"], "lng": loc["lng"],
                "temperature": round(c.get("temperature_2m", 0), 1),
                "humidity": c.get("relative_humidity_2m"),
                "precipitation_mm": c.get("precipitation", 0),
                "wind_kmh": round(c.get("wind_speed_10m", 0), 1),
                "weather_code": code,
                "description": _WMO.get(code, "Fair"),
                "source": "open-meteo",
            })
        except Exception:
            continue
    return out


@router.get("")
def list_trail_weather():
    """Live weather for the 4 default trail locations (cached 15 min)."""
    now = datetime.utcnow()
    if _list_cache["at"] and _list_cache["data"] and (now - _list_cache["at"]) < timedelta(minutes=CACHE_TTL_MINUTES):
        return _list_cache["data"]
    data = _fetch_trail_weather()
    if data:
        _list_cache.update(at=now, data=data)
        return data
    if _list_cache["data"]:  # serve last good data rather than nothing
        return _list_cache["data"]
    raise HTTPException(503, "Live weather is temporarily unavailable.")


@router.get("/{lat}/{lng}")
def fetch_weather(lat: float, lng: float, db: Session = Depends(get_db)):
    from models.advisory import WeatherCache
    key = _location_key(lat, lng)
    cached = db.query(WeatherCache).filter(WeatherCache.location_key == key).first()
    if cached and cached.payload.get("source") != "mock" and (datetime.utcnow() - cached.fetched_at) < timedelta(minutes=CACHE_TTL_MINUTES):
        return cached.payload

    if not settings.OWM_API_KEY:
        raise HTTPException(503, "Live weather is unavailable. Configure OWM_API_KEY to enable it.")

    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={settings.OWM_API_KEY}"
    resp = httpx.get(url, timeout=5); resp.raise_for_status()
    d = resp.json(); main = d.get("main",{}); wind = d.get("wind",{})
    w = d.get("weather",[{}])[0]; rain = d.get("rain",{})
    payload = {
        "temperature": round(main.get("temp",0)-273.15,1), "feels_like": round(main.get("feels_like",0)-273.15,1),
        "humidity": main.get("humidity",0), "description": w.get("description","").capitalize(),
        "icon": w.get("icon","01d"), "wind_speed": wind.get("speed",0),
        "wind_dir": _deg_to_compass(wind.get("deg",0)),
        "rain_warning": rain.get("1h",0)>10, "storm_warning": "thunderstorm" in w.get("main","").lower(),
        "uv_index": None, "visibility_km": round(d.get("visibility",10000)/1000,1), "source": "openweathermap",
    }

    if cached:
        cached.payload = payload; cached.fetched_at = datetime.utcnow()
    else:
        db.add(WeatherCache(id=str(uuid.uuid4()), location_key=key, payload=payload))
    db.commit()
    return payload
