/**
 * dashboard/src/components/GraphSkeleton.jsx
 *
 * Shimmering placeholder shown in GraphCanvas's spot while a case's
 * graph is being fetched (api.queryCase), so switching cases doesn't
 * flash an empty canvas before the sample-data fallback or real data
 * arrives.
 */

export default function GraphSkeleton() {
  return (
    <div className="graph-canvas-wrapper graph-skeleton">
      <div className="graph-skeleton-nodes">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="graph-skeleton-node" style={{ animationDelay: `${i * 90}ms` }} />
        ))}
      </div>
    </div>
  )
}
