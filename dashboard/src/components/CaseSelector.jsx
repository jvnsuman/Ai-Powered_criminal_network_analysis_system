/**
 * dashboard/src/components/CaseSelector.jsx
 *
 * Dropdown of every case the logged-in user is authorized to see
 * (api/routes/cases.py's GET /cases/, already role/agency-scoped
 * server-side). Selecting one drives GraphCanvas/EvidencePanel/
 * IngestionForm in App.jsx.
 */

import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function CaseSelector({ selectedCaseId, onSelectCase }) {
  const [cases, setCases] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    api
      .listCases()
      .then((data) => setCases(data.cases || []))
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <div className="case-selector case-selector-error">{error}</div>

  return (
    <select
      className="case-selector"
      value={selectedCaseId || ''}
      onChange={(e) => onSelectCase(e.target.value)}
    >
      <option value="" disabled>
        Select a case
      </option>
      {cases.map((c) => (
        <option key={c.id} value={c.id}>
          {c.title}
        </option>
      ))}
    </select>
  )
}
