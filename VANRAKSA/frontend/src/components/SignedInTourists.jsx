import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'

/** Tourists who have entered the app (name, phone, entry time in IST) — for Rangers / Admin. */
export default function SignedInTourists() {
  const [tourists, setTourists] = useState([])
  const liveTourists = tourists.filter(t => t.location_updated_at && Date.now() - new Date(t.location_updated_at).getTime() <= 90000)
  const movingTourists = liveTourists.filter(t => Number(t.speed_kmh) >= 1)

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/auth/tourists')
      setTourists(data || [])
    } catch { /* keep last list */ }
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 10000)
    return () => clearInterval(id)
  }, [load])

  return (
    <div className="bg-surface hairline-border rounded p-md shadow-sm">
      <div className="flex items-center justify-between hairline-border-b pb-sm mb-md">
        <div className="font-label-caps text-label-caps text-tertiary">SIGNED-IN TOURISTS</div>
        <div className="flex items-center gap-sm font-data-mono text-[10px]">
          <span className="text-outline">{tourists.length} TOTAL</span>
          <span className="text-secondary">{liveTourists.length} LIVE</span>
          <span className="text-primary">{movingTourists.length} MOVING</span>
        </div>
      </div>
      <p className="font-data-mono text-[10px] text-outline mb-sm">
        LOCATION FRESHNESS, MOVEMENT, AND CONFIGURED-ZONE PROXIMITY · NOT AN AI PREDICTION
      </p>
      <div className="divide-y divide-outline/10 max-h-64 overflow-y-auto">
        {tourists.map(t => (
          <div key={t.id} className="py-sm first:pt-0 last:pb-0">
            <div className="font-body-md text-sm text-on-surface font-semibold truncate">{t.full_name}</div>
            {t.dtid_code && <div className="font-data-mono text-[10px] text-secondary">ID · {t.dtid_code}</div>}
            <div className="flex items-center justify-between gap-sm font-data-mono text-xs">
              <a href={`tel:${t.phone}`} className="text-primary hover:underline flex items-center gap-xs">
                <span className="material-symbols-outlined text-xs">call</span>{t.phone}
              </a>
              <span className="text-outline text-[10px]">{t.last_login_ist}</span>
            </div>
            {Number.isFinite(t.lat) && Number.isFinite(t.lng) && (
              <div className="mt-xs flex flex-wrap items-center justify-between gap-xs font-data-mono text-[10px]">
                <span className="text-on-surface-variant">
                  {Number(t.lat).toFixed(5)}°, {Number(t.lng).toFixed(5)}°
                  {t.speed_kmh != null ? ` · ${Number(t.speed_kmh).toFixed(1)} km/h` : ''}
                </span>
                <span className={t.risk_level === 'HIGH' ? 'text-error font-bold' : t.risk_level === 'ELEVATED' ? 'text-primary font-bold' : 'text-secondary'}>
                  ZONE RISK: {t.risk_level || 'UNASSESSED'}{t.risk_score != null ? ` · ${t.risk_score}/100` : ''}
                </span>
                <Link
                  to={`/map?lat=${t.lat}&lng=${t.lng}&name=${encodeURIComponent(t.full_name || 'Tourist')}&phone=${encodeURIComponent(t.phone || '')}&type=TOURIST&dtid=${encodeURIComponent(t.dtid_code || '')}`}
                  className="text-primary hover:underline font-bold"
                >
                  TRACK
                </Link>
                {t.risk_reason && <span className="basis-full text-outline">{t.risk_reason}</span>}
              </div>
            )}
          </div>
        ))}
        {!tourists.length && (
          <p className="font-data-mono text-xs text-on-surface-variant text-center py-md">NO TOURISTS SIGNED IN YET</p>
        )}
      </div>
    </div>
  )
}
