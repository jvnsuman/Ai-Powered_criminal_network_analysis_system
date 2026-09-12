/**
 * MapPanel.jsx
 *
 * Geospatial view of LOCATION-type entities in the current graph.
 *
 * Honest scope note: LOCATION entities extracted by
 * nlp/extraction.py are free-text strings ("MG Road", "Shastri Nagar")
 * with no lat/lng — there is no geocoding step anywhere in the
 * pipeline yet (not in nlp/extraction.py, not in schema/entities.py's
 * Entity dataclass, which has no coordinate fields). So this renders
 * a labeled relative-position placeholder from the location strings
 * actually present in the graph, NOT a real basemap with real
 * coordinates. This is intentionally different from the mockup's
 * detailed India outline with pinned cities, which implies real
 * geocoding that does not exist in this codebase.
 *
 * To make this real: add latitude/longitude to schema.entities.Entity
 * for LOCATION type, populate it via a geocoding API call in
 * nlp/extraction.py's location-handling path, then swap this
 * component's placeholder circles for a real map library (e.g.
 * react-leaflet) plotting real coordinates.
 */

import { MapPin } from 'lucide-react'

// Deterministic pseudo-position from a string, so the same location
// name always lands in the same spot on screen (not random per
// render), without pretending it's a geocoded coordinate.
function pseudoPosition(label) {
  let hash = 0
  for (let i = 0; i < label.length; i++) hash = (hash * 31 + label.charCodeAt(i)) >>> 0
  return { x: 15 + (hash % 70), y: 15 + ((hash >> 8) % 70) }
}

export default function MapPanel({ locations }) {
  return (
    <div className="panel map-panel">
      <div className="panel-header">
        <h3>
          <MapPin size={14} />
          Location Clusters
        </h3>
      </div>
      {locations.length === 0 ? (
        <p className="panel-status">No location entities in this graph yet.</p>
      ) : (
        <>
          <div className="map-placeholder">
            {locations.map((loc) => {
              const pos = pseudoPosition(loc.label)
              return (
                <div
                  key={loc.id}
                  className="map-pin"
                  style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
                  title={loc.label}
                >
                  <MapPin size={16} strokeWidth={2.4} />
                  <span className="map-pin-label">{loc.label}</span>
                </div>
              )
            })}
          </div>
          <p className="map-panel-note">
            Relative placement only — no geocoding is wired up yet (see component source).
          </p>
        </>
      )}
    </div>
  )
}
