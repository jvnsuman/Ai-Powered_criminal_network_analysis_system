/**
 * dashboard/src/components/GraphCanvas.jsx
 *
 * Interactive network graph canvas using Cytoscape.js. Required
 * interactions:
 * - click a node -> notify parent (drives EvidencePanel)
 * - hover -> tooltip (name/type for nodes, relationship/weight for edges)
 * - zoom and pan (Cytoscape defaults, plus explicit on-screen controls)
 * - filter/search integration with SearchBar (dim non-matches, highlight matches)
 * - expand/collapse dense subgraphs (hubs with many neighbors collapse
 *   behind a single "+N more" node until clicked)
 *
 * Layout: a concentric layout anchored on the "main suspect" (the
 * highest-degree PERSON entity — see findMainEntityId) so that node
 * always sits at the visual center, with everything else radiating
 * outward by degree, rather than a force-directed layout that could
 * place the most important entity anywhere.
 *
 * graphData shape: { nodes: [{id, label, entity_type}],
 *                     edges: [{id, source, target, relationship_type, weight}] }
 */

import { Maximize2, Network as NetworkIcon, ZoomIn, ZoomOut } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import cytoscape from 'cytoscape'

// Nodes with more hidden neighbors than this get collapsed behind a
// single "+N more" expander node on initial render.
const COLLAPSE_THRESHOLD = 4
const VISIBLE_NEIGHBORS_WHEN_COLLAPSED = 2

const ENTITY_COLORS = {
  person: '#38bdf8',
  location: '#f5b942',
  vehicle: '#a78bfa',
  phone: '#2dd4bf',
  organization: '#f2637a',
  event: '#9aa3b8',
}

const LEGEND_ITEMS = [
  { label: 'Person', color: ENTITY_COLORS.person },
  { label: 'Location', color: ENTITY_COLORS.location },
  { label: 'Vehicle', color: ENTITY_COLORS.vehicle },
  { label: 'Phone', color: ENTITY_COLORS.phone },
  { label: 'Organization', color: ENTITY_COLORS.organization },
  { label: 'Event', color: ENTITY_COLORS.event },
]

/**
 * Pick the node to anchor at the center of the layout — the "main
 * suspect." Prefers the highest-degree PERSON entity (a criminal
 * network's central figure should be a person, not a location or
 * event that merely happens to have many connections); falls back to
 * the highest-degree node overall if the graph has no person entities.
 */
function findMainEntityId(graphData) {
  const degree = {}
  graphData.nodes.forEach((n) => { degree[n.id] = 0 })
  graphData.edges.forEach((e) => {
    degree[e.source] = (degree[e.source] || 0) + 1
    degree[e.target] = (degree[e.target] || 0) + 1
  })

  const personNodes = graphData.nodes.filter((n) => n.entity_type === 'person')
  const candidates = personNodes.length > 0 ? personNodes : graphData.nodes
  if (candidates.length === 0) return null

  return candidates.reduce((best, n) => ((degree[n.id] || 0) > (degree[best.id] || 0) ? n : best), candidates[0]).id
}

/** Cytoscape stylesheet: node/edge colors, sizes, and the dimmed/highlighted/expander state classes. */
function buildStylesheet() {
  return [
    {
      selector: 'node',
      style: {
        'background-color': (ele) => ENTITY_COLORS[ele.data('entity_type')] || '#999',
        label: 'data(label)',
        color: '#eef1f7',
        'font-family': 'Inter, sans-serif',
        'font-size': 11,
        'font-weight': 500,
        'text-valign': 'bottom',
        'text-margin-y': 8,
        width: 36,
        height: 36,
        'border-width': 3,
        'border-color': '#0b0d12',
        'transition-property': 'border-width, border-color, opacity',
        'transition-duration': 120,
      },
    },
    {
      // The synthetic "+N more" node created when a hub's neighbors are collapsed.
      selector: 'node.expander',
      style: {
        shape: 'round-rectangle',
        'background-color': '#232838',
        width: 'label',
        height: 26,
        padding: '7px',
        'font-size': 10,
        'font-weight': 500,
        color: '#8b93a7',
        'border-width': 1,
        'border-color': '#3a4258',
        'border-style': 'dashed',
      },
    },
    {
      // Applied to everything that doesn't match the current search query.
      selector: 'node.dimmed',
      style: { opacity: 0.12 },
    },
    {
      // Applied to nodes that do match the current search query.
      selector: 'node.highlighted',
      style: { 'border-width': 3, 'border-color': '#f5b942' },
    },
    {
      // Applied to the "main suspect" node — the highest-degree PERSON
      // entity, centered by the concentric layout below. A lightweight,
      // client-side stand-in for graph.build.highlight_influencer until
      // that's exposed over the API: computed from the already-loaded
      // graph, not a new backend call.
      selector: 'node.main-suspect',
      style: {
        'border-width': 3,
        'border-color': '#2dd4bf',
        'border-style': 'double',
        width: 46,
        height: 46,
        'z-index': 10,
      },
    },
    {
      // Subtle "lift" on hover — reinforces that nodes are clickable.
      selector: 'node.node-hover',
      style: { width: 42, height: 42 },
    },
    {
      selector: 'edge',
      style: {
        width: (ele) => 1.4 + Math.min(Number(ele.data('weight')) || 1, 6),
        'line-color': '#3a4258',
        'target-arrow-color': '#3a4258',
        'target-arrow-shape': 'triangle',
        'arrow-scale': 0.9,
        'curve-style': 'bezier',
        opacity: 0.75,
        'transition-property': 'opacity',
        'transition-duration': 120,
      },
    },
    {
      selector: 'edge.dimmed',
      style: { opacity: 0.04 },
    },
  ]
}

export default function GraphCanvas({ graphData, onNodeSelect, searchQuery }) {
  const containerRef = useRef(null)
  const cyRef = useRef(null)
  // Tracks collapsed hubs: expanderId -> {hubId, hiddenNodeIds, hiddenEdgeIds}
  // so expandNode() knows what to restore when a "+N more" node is clicked.
  const collapsedSetsRef = useRef(new Map())
  const [tooltip, setTooltip] = useState(null) // {x, y, lines: []}

  // Build (or rebuild) the Cytoscape instance whenever graphData changes.
  useEffect(() => {
    if (!containerRef.current) return undefined
    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) return undefined

    const elements = [
      ...graphData.nodes.map((n) => ({
        data: { id: n.id, label: n.label, entity_type: n.entity_type },
      })),
      ...graphData.edges.map((e) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          relationship_type: e.relationship_type,
          weight: e.weight ?? 1,
        },
      })),
    ]

    const mainEntityId = findMainEntityId(graphData)

    // Concentric layout centered on mainEntityId — other nodes radiate
    // outward by degree, so more-connected entities sit closer in.
    const centeredLayoutOptions = {
      name: 'concentric',
      animate: false,
      padding: 40,
      minNodeSpacing: 50,
      concentric: (node) => (node.id() === mainEntityId ? 1000 : node.degree() + 1),
      levelWidth: () => 2,
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: buildStylesheet(),
      layout: centeredLayoutOptions,
      wheelSensitivity: 0.2,
      // zoom + pan are enabled by default; kept explicit for clarity
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
      minZoom: 0.2,
      maxZoom: 3,
    })
    cyRef.current = cy
    collapsedSetsRef.current = new Map()

    if (mainEntityId) cy.$id(mainEntityId).addClass('main-suspect')

    // Click a node -> notify parent (drives EvidencePanel), or expand
    // it if it's a collapsed-hub placeholder.
    cy.on('tap', 'node', (evt) => {
      const node = evt.target
      if (node.hasClass('expander')) {
        expandNode(node.id())
        return
      }
      onNodeSelect?.(node.id())
    })

    // Clicking empty canvas clears the current selection.
    cy.on('tap', (evt) => {
      if (evt.target === cy) onNodeSelect?.(null)
    })

    // Hover tooltip: node name/type, or edge relationship/weight.
    cy.on('mouseover', 'node', (evt) => {
      const node = evt.target
      if (node.hasClass('expander')) return
      node.addClass('node-hover')
      const pos = node.renderedPosition()
      setTooltip({
        x: pos.x,
        y: pos.y,
        lines: [node.data('label'), `type: ${node.data('entity_type')}`],
      })
    })
    cy.on('mouseover', 'edge', (evt) => {
      const edge = evt.target
      const pos = edge.midpoint()
      setTooltip({
        x: pos.x,
        y: pos.y,
        lines: [`relationship: ${edge.data('relationship_type')}`, `weight: ${edge.data('weight')}`],
      })
    })
    cy.on('mouseout', 'node', (evt) => evt.target.removeClass('node-hover'))
    cy.on('mouseout', 'node, edge', () => setTooltip(null))

    // Restore a collapsed hub's hidden neighbors and remove its "+N more" placeholder.
    function expandNode(expanderId) {
      const entry = collapsedSetsRef.current.get(expanderId)
      if (!entry) return
      cy.batch(() => {
        cy.$id(expanderId).remove()
        entry.hiddenNodeIds.forEach((id) => cy.$id(id).restore())
        entry.hiddenEdgeIds.forEach((id) => cy.$id(id).restore())
      })
      collapsedSetsRef.current.delete(expanderId)
    }

    // On first render, collapse any hub with more than
    // COLLAPSE_THRESHOLD neighbors down to
    // VISIBLE_NEIGHBORS_WHEN_COLLAPSED, replacing the rest with a
    // single clickable "+N more" node so dense subgraphs stay readable.
    cy.ready(() => {
      cy.batch(() => {
        cy.nodes().forEach((node) => {
          if (node.hasClass('expander')) return
          const neighborEdges = node.connectedEdges()
          if (neighborEdges.length <= COLLAPSE_THRESHOLD) return

          const edgesToHide = neighborEdges.slice(VISIBLE_NEIGHBORS_WHEN_COLLAPSED)
          const nodesToHide = edgesToHide
            .connectedNodes()
            .filter((n) => n.id() !== node.id())

          if (nodesToHide.length === 0) return

          const expanderId = `expander-${node.id()}`
          cy.add({
            data: { id: expanderId, label: `+${nodesToHide.length} more` },
            classes: 'expander',
            position: node.position(),
          })
          cy.add({
            data: { id: `${expanderId}-edge`, source: node.id(), target: expanderId },
          })

          collapsedSetsRef.current.set(expanderId, {
            hubId: node.id(),
            hiddenNodeIds: nodesToHide.map((n) => n.id()),
            hiddenEdgeIds: edgesToHide.map((e) => e.id()),
          })

          edgesToHide.remove()
          nodesToHide.remove()
        })
      })
      cy.layout(centeredLayoutOptions).run()
    })

    return () => cy.destroy()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphData])

  // Re-apply the dim/highlight classes whenever the search query changes.
  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    const query = (searchQuery || '').trim().toLowerCase()

    cy.batch(() => {
      if (!query) {
        cy.elements().removeClass('dimmed highlighted')
        return
      }
      const matches = cy.nodes().filter(
        (n) => !n.hasClass('expander') && (n.data('label') || '').toLowerCase().includes(query)
      )
      cy.elements().addClass('dimmed').removeClass('highlighted')
      matches.removeClass('dimmed').addClass('highlighted')
      matches.connectedEdges().removeClass('dimmed')
      matches.neighborhood('node').removeClass('dimmed')
    })
  }, [searchQuery])

  function zoomBy(factor) {
    const cy = cyRef.current
    if (!cy) return
    cy.animate({ zoom: cy.zoom() * factor, center: { eles: cy.elements() } }, { duration: 150 })
  }

  function resetView() {
    const cy = cyRef.current
    if (!cy) return
    cy.animate({ fit: { eles: cy.elements(), padding: 30 } }, { duration: 200 })
  }

  const hasData = graphData && graphData.nodes?.length > 0
  const usedEntityTypes = hasData ? new Set(graphData.nodes.map((n) => n.entity_type)) : new Set()

  return (
    <div className="graph-canvas-wrapper">
      <div ref={containerRef} className="graph-canvas" />
      {tooltip && (
        <div className="graph-tooltip" style={{ left: tooltip.x + 12, top: tooltip.y + 12 }}>
          {tooltip.lines.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
      )}
      {hasData && (
        <>
          <div className="graph-legend">
            {LEGEND_ITEMS.filter((item) => usedEntityTypes.has(item.label.toLowerCase())).map((item) => (
              <div className="graph-legend-item" key={item.label}>
                <span className="graph-legend-dot" style={{ background: item.color }} />
                {item.label}
              </div>
            ))}
            <div className="graph-legend-item">
              <span className="graph-legend-dot graph-legend-dot-ring" />
              Main suspect
            </div>
          </div>
          <div className="graph-controls">
            <button type="button" className="graph-control-button" onClick={() => zoomBy(1.3)} aria-label="Zoom in">
              <ZoomIn size={16} />
            </button>
            <button type="button" className="graph-control-button" onClick={() => zoomBy(0.75)} aria-label="Zoom out">
              <ZoomOut size={16} />
            </button>
            <button type="button" className="graph-control-button" onClick={resetView} aria-label="Fit to view">
              <Maximize2 size={15} />
            </button>
          </div>
        </>
      )}
      {!hasData && (
        <div className="graph-empty-state">
          <NetworkIcon size={30} />
          No graph data to display.
        </div>
      )}
    </div>
  )
}
