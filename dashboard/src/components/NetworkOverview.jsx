/**
 * NetworkOverview.jsx
 *
 * Donut breakdown of relationship types by connected entity type,
 * computed from the currently-loaded graph's edges (real data, not
 * the mockup's fixed 58,362/42%/18%/etc. figures) — see
 * computeOverviewSegments in Dashboard.jsx for how this is derived
 * from graphData.edges + graphData.nodes.
 */

const COLOR_VAR = {
  person: '--violet',
  organization: '--primary',
  location: '--teal',
  vehicle: '--amber',
  phone: '--danger',
}

export default function NetworkOverview({ segments, total }) {
  let cumulative = 0
  const radius = 54
  const circumference = 2 * Math.PI * radius

  return (
    <div className="panel network-overview">
      <div className="panel-header">
        <h3>Network Overview</h3>
      </div>
      <div className="donut-wrap">
        <svg viewBox="0 0 140 140" className="donut-svg">
          {segments.map((s) => {
            const dash = (s.pct / 100) * circumference
            const gap = circumference - dash
            const offset = -((cumulative / 100) * circumference)
            cumulative += s.pct
            return (
              <circle
                key={s.key}
                cx="70"
                cy="70"
                r={radius}
                fill="none"
                stroke={`var(${COLOR_VAR[s.key] || '--primary'})`}
                strokeWidth="18"
                strokeDasharray={`${dash} ${gap}`}
                strokeDashoffset={offset}
                transform="rotate(-90 70 70)"
              />
            )
          })}
        </svg>
        <div className="donut-center">
          <div className="donut-center-value">{total.toLocaleString()}</div>
          <div className="donut-center-label">Relationships</div>
        </div>
      </div>
      <ul className="donut-legend">
        {segments.map((s) => (
          <li key={s.key}>
            <span className="donut-legend-dot" style={{ background: `var(${COLOR_VAR[s.key] || '--primary'})` }} />
            {s.label} — {s.pct}%
          </li>
        ))}
      </ul>
    </div>
  )
}
