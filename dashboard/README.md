# Dashboard

React app — Cytoscape.js graph UI, investigator-facing.

Status: [TODO] — Dec P1, not started. Sep slice ships a static
render/screenshot only (see graph.build.render_graph), not this app.

## Components (project notes Section 12)

- `GraphCanvas` — interactive render: click, hover, zoom/pan, filter,
  expand/collapse. The graph canvas cannot ship as a static image —
  this is a hard requirement, not a nice-to-have.
- `EvidencePanel` — shows source documents for the selected node,
  powered by `api/routes/evidence.py`
- `SearchBar` — filter/isolate by name, phone, or alias
- `CaseSummaryCards` — entities linked, key influencers count, flagged
  patterns count

## Setup (once started)

```bash
npm install
npm run dev
```
