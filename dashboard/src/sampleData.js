/**
 * dashboard/src/sampleData.js
 *
 * Synthetic demo graph — NOT real case data. Shown only when the
 * backend reports its graph pipeline as not-yet-implemented (see
 * api/routes/query.py's 501 response), so GraphCanvas/SearchBar/
 * CaseSummaryCards are demonstrable before graph.build exists.
 * Mirrors the project's own data/generate_synthetic.py approach for
 * the same reason. Always shown behind a clearly-labeled banner (see
 * App.jsx's usingSampleData state) — never silently swapped in for a
 * real case's data.
 */

export const SAMPLE_GRAPH = {
  caseId: 'DEMO-CASE',
  nodes: [
    { id: 'p1', label: 'Raju Sharma', entity_type: 'person' },
    { id: 'p2', label: 'Anita Verma', entity_type: 'person' },
    { id: 'p3', label: 'Sunil Yadav', entity_type: 'person' },
    { id: 'ph1', label: '+91-9876543210', entity_type: 'phone' },
    { id: 'ph2', label: '+91-9123456780', entity_type: 'phone' },
    { id: 'loc1', label: 'Patna Junction', entity_type: 'location' },
    { id: 'veh1', label: 'MH-04 AB 1234', entity_type: 'vehicle' },
    { id: 'org1', label: 'Shipping Front Co.', entity_type: 'organization' },
    { id: 'evt1', label: 'Meeting — 12 Mar', entity_type: 'event' },
  ],
  edges: [
    { id: 'e1', source: 'p1', target: 'ph1', relationship_type: 'calls', weight: 3 },
    { id: 'e2', source: 'p2', target: 'ph2', relationship_type: 'calls', weight: 1 },
    { id: 'e3', source: 'p1', target: 'loc1', relationship_type: 'present_at', weight: 1 },
    { id: 'e4', source: 'p2', target: 'loc1', relationship_type: 'present_at', weight: 1 },
    { id: 'e5', source: 'p3', target: 'veh1', relationship_type: 'owns', weight: 1 },
    { id: 'e6', source: 'evt1', target: 'org1', relationship_type: 'associated_with', weight: 2 },
    { id: 'e7', source: 'p1', target: 'evt1', relationship_type: 'participates_in', weight: 1 },
    { id: 'e8', source: 'p2', target: 'evt1', relationship_type: 'participates_in', weight: 1 },
    { id: 'e9', source: 'p3', target: 'evt1', relationship_type: 'participates_in', weight: 1 },
  ],
  stats: {
    entitiesLinked: 9,
    keyInfluencers: 1,
    flaggedPatterns: 1,
  },
}
