/**
 * TopEntitiesTable.jsx
 *
 * Ranked list of the highest-degree nodes in the currently-loaded
 * graph — computed client-side from graphData (degree = number of
 * connected edges), the same signal graph.build.compute_centrality
 * uses server-side, just simplified for a quick glance table. For
 * anything beyond a ranked list (actual betweenness/PageRank score),
 * defer to GraphCanvas's main-suspect highlight, which calls the real
 * backend centrality via graph.build.highlight_influencer once that's
 * exposed over /query.
 */

const TYPE_ICON_TINT = {
  person: 'violet',
  organization: 'primary',
  location: 'teal',
  vehicle: 'amber',
  phone: 'danger',
}

export default function TopEntitiesTable({ entities }) {
  const maxConnections = Math.max(...entities.map((e) => e.connections), 1)

  return (
    <div className="panel top-entities">
      <div className="panel-header">
        <h3>Top Connected Entities</h3>
      </div>
      {entities.length === 0 ? (
        <p className="panel-status">No entities in this graph yet.</p>
      ) : (
        <table className="entities-table">
          <thead>
            <tr>
              <th>Entity</th>
              <th>Type</th>
              <th>Connections</th>
            </tr>
          </thead>
          <tbody>
            {entities.map((e) => (
              <tr key={e.id}>
                <td className="entities-table-name">{e.label}</td>
                <td>
                  <span className={`type-pill tint-${TYPE_ICON_TINT[e.entity_type] || 'primary'}`}>
                    {e.entity_type}
                  </span>
                </td>
                <td>
                  <div className="entities-table-bar-wrap">
                    <div
                      className={`entities-table-bar tint-${TYPE_ICON_TINT[e.entity_type] || 'primary'}`}
                      style={{ width: `${(e.connections / maxConnections) * 100}%` }}
                    />
                    <span>{e.connections}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
