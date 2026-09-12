/**
 * MetricStrip.jsx
 *
 * Five summary metric cards (entities, relationships, locations,
 * vehicles, phone numbers) with a trend delta, matching the new
 * mockup direction. Renders from `metrics` which the parent page
 * computes from the loaded case graph (see Dashboard.jsx) — never
 * hardcoded, so this shows real counts for whatever case/sample data
 * is currently loaded rather than the mockup's fixed demo numbers.
 *
 * A metric's `trend` field is optional: real per-case week-over-week
 * deltas require historical snapshots the backend doesn't persist yet
 * (see api/routes/query.py's docstring on what's still missing), so
 * trend is only shown when the caller actually has one to report.
 */

import { MapPin, Network, Phone, Truck, Users } from 'lucide-react'

const ICONS = {
  entities: { icon: Users, tint: 'violet' },
  relationships: { icon: Network, tint: 'danger' },
  locations: { icon: MapPin, tint: 'teal' },
  vehicles: { icon: Truck, tint: 'amber' },
  phones: { icon: Phone, tint: 'primary' },
}

export default function MetricStrip({ metrics }) {
  return (
    <div className="metric-strip">
      {metrics.map((m) => {
        const conf = ICONS[m.key] || ICONS.entities
        const Icon = conf.icon
        return (
          <div className="metric-card" key={m.key}>
            <div className={`metric-card-icon tint-${conf.tint}`}>
              <Icon size={19} strokeWidth={2.2} />
            </div>
            <div className="metric-card-body">
              <div className="metric-card-label">{m.label}</div>
              <div className="metric-card-value">{m.value.toLocaleString()}</div>
              {typeof m.trend === 'number' && (
                <div className={`metric-card-trend ${m.trend >= 0 ? 'up' : 'down'}`}>
                  {m.trend >= 0 ? '↑' : '↓'} {Math.abs(m.trend)}%
                  <span className="metric-card-trend-label">vs. last 7 days</span>
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
