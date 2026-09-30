"""Weather router — sync wrapper."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from middleware.rbac import get_current_user
import httpx, uuid
from datetime import datetime, timedelta
from config import settings

router = APIRouter(prefix="/weather", tags=["weather"])

CACHE_TTL_MINUTES = 15

def _location_key(lat, lng): return f"lat:{round(lat,2)}_lng:{round(lng,2)}"
def _deg_to_compass(deg):
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[round(deg/22.5)%16]


@router.get("/{lat}/{lng}")
def fetch_weather(lat: float, lng: float, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
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
