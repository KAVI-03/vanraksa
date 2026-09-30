const GEOCODER_URL = 'https://photon.komoot.io/api/'
const WALKING_ROUTER_URL = 'https://routing.openstreetmap.de/routed-foot/route/v1/driving'

export async function geocodeDestination(query, near) {
  const params = new URLSearchParams({ q: query, limit: '5' })
  if (near) {
    params.set('lat', String(near.lat))
    params.set('lon', String(near.lng))
  }

  const response = await fetch(`${GEOCODER_URL}?${params}`)
  if (!response.ok) throw new Error('Destination search is unavailable. Retry in a moment.')

  const data = await response.json()
  return (data.features || []).map(feature => {
    const properties = feature.properties || {}
    const [lng, lat] = feature.geometry.coordinates
    const locality = [properties.city, properties.state, properties.country].filter(Boolean).join(', ')
    return {
      name: properties.name || properties.street || properties.city || 'Destination',
      label: [properties.name || properties.street, locality].filter(Boolean).join(', '),
      lat,
      lng,
    }
  })
}

const formatInstruction = step => {
  const maneuver = step.maneuver || {}
  const action = {
    depart: 'Start',
    arrive: 'Arrive',
    turn: 'Turn',
    continue: 'Continue',
    merge: 'Merge',
    roundabout: 'Enter the roundabout',
    'exit roundabout': 'Exit the roundabout',
    'new name': 'Continue',
  }[maneuver.type] || 'Continue'
  const direction = maneuver.modifier ? ` ${maneuver.modifier}` : ''
  const street = step.name ? ` onto ${step.name}` : ''
  return `${action}${direction}${street}`
}

export async function getWalkingRoutes(start, destination) {
  const coordinates = `${start.lng},${start.lat};${destination.lng},${destination.lat}`
  const params = new URLSearchParams({
    alternatives: 'true',
    steps: 'true',
    overview: 'full',
    geometries: 'geojson',
  })
  const response = await fetch(`${WALKING_ROUTER_URL}/${coordinates}?${params}`)
  if (!response.ok) throw new Error('Walking routes are unavailable for this destination.')

  const data = await response.json()
  if (data.code !== 'Ok' || !data.routes?.length) {
    throw new Error('No walking route was found for this destination.')
  }

  return data.routes.map(route => ({
    distanceM: route.distance,
    durationSec: route.duration,
    coordinates: route.geometry.coordinates.map(([lng, lat]) => [lat, lng]),
    geometry: route.geometry,
    steps: route.legs.flatMap(leg => leg.steps.map(step => ({
      instruction: formatInstruction(step),
      distanceM: step.distance,
      location: step.maneuver?.location
        ? [step.maneuver.location[1], step.maneuver.location[0]]
        : null,
    }))),
  }))
}
