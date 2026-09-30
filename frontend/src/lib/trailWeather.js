// Weather + derived alerts for the 4 default trail locations.
import { SURVEYED_TRAILS } from './trailsData'

const WMO = {
  0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast', 45: 'Fog', 48: 'Rime fog',
  51: 'Light drizzle', 53: 'Drizzle', 55: 'Heavy drizzle', 61: 'Light rain', 63: 'Rain', 65: 'Heavy rain',
  71: 'Light snow', 73: 'Snow', 75: 'Heavy snow', 77: 'Snow grains', 80: 'Rain showers',
  81: 'Heavy showers', 82: 'Violent showers', 85: 'Snow showers', 86: 'Heavy snow showers',
  95: 'Thunderstorm', 96: 'Thunderstorm with hail', 99: 'Severe thunderstorm with hail',
}

const CITY = { kasauli: 'Kasauli', dzukou: 'Dzukou Valley', goechala: 'Goechala', 'david-scott': 'David Scott Trail' }

/** Direct browser fallback (Open-Meteo, no key) if the backend list endpoint is unreachable. */
export async function fetchTrailWeatherDirect() {
  const results = await Promise.allSettled(SURVEYED_TRAILS.map(async trail => {
    const { lat, lng } = trail.startPoint
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}` +
      '&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m'
    const res = await fetch(url)
    if (!res.ok) throw new Error('weather')
    const c = (await res.json()).current || {}
    const code = Number(c.weather_code ?? 0)
    return {
      id: trail.id, city: CITY[trail.id] || trail.name,
      temperature: Math.round((c.temperature_2m ?? 0) * 10) / 10,
      humidity: c.relative_humidity_2m, precipitation_mm: c.precipitation ?? 0,
      wind_kmh: c.wind_speed_10m ?? 0, weather_code: code, description: WMO[code] || 'Fair',
    }
  }))
  return results.filter(r => r.status === 'fulfilled').map(r => r.value)
}

/** Alerts derived from live weather + surveyed trail status for the 4 default locations. */
export function deriveTrailAlerts(weather = []) {
  const alerts = []
  for (const w of weather) {
    const code = Number(w.weather_code)
    if (code >= 95) alerts.push(`⚠ ${w.city}: ${w.description} — avoid exposed ridges`)
    else if ([65, 75, 82, 86].includes(code)) alerts.push(`⚠ ${w.city}: ${w.description} — trail conditions hazardous`)
    else if ([45, 48].includes(code)) alerts.push(`⚠ ${w.city}: Fog — low visibility, stay on marked route`)
    if (Number(w.wind_kmh) >= 40) alerts.push(`⚠ ${w.city}: Strong winds ${Math.round(w.wind_kmh)} km/h`)
    if (Number(w.temperature) <= 3) alerts.push(`⚠ ${w.city}: Near-freezing ${w.temperature}°C — cold exposure risk`)
    if (Number(w.temperature) >= 35) alerts.push(`⚠ ${w.city}: Heat ${w.temperature}°C — carry water`)
  }
  for (const t of SURVEYED_TRAILS) {
    if (t.status === 'warning') alerts.push(`⚠ ${t.name.split('(')[0].trim()}: ${t.safetyRating} — ${t.permit.toLowerCase()}`)
    if (t.permit.includes('ILP')) alerts.push(`ℹ ${t.region}: Inner Line Permit required for ${t.name.split('(')[0].trim()}`)
  }
  return alerts
}
