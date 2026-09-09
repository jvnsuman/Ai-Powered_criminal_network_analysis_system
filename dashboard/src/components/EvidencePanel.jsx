/**
 * dashboard/src/components/EvidencePanel.jsx
 *
 * Right-panel evidence trail for the currently-selected graph node —
 * the source documents backing that entity, fetched from
 * api/routes/evidence.py. Handles four states: idle (nothing
 * selected), loading, pending (backend pipeline not implemented yet),
 * and ready (with or without results).
 */

import { AlertCircle, Clock, FileSearch, FileText, MousePointerClick } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function EvidencePanel({ selectedEntityId }) {
  const [state, setState] = useState({ status: 'idle', evidence: [], message: null })

  useEffect(() => {
    if (!selectedEntityId) {
      setState({ status: 'idle', evidence: [], message: null })
      return
    }
    let cancelled = false
    setState({ status: 'loading', evidence: [], message: null })

    api
      .getEvidence(selectedEntityId)
      .then((data) => {
        if (cancelled) return
        setState({ status: 'ready', evidence: data.evidence || [], message: null })
      })
      .catch((err) => {
        if (cancelled) return
        if (err.pending) {
          setState({
            status: 'pending',
            evidence: [],
            message: 'The evidence-trail pipeline is not connected yet.',
          })
        } else {
          setState({ status: 'error', evidence: [], message: err.message })
        }
      })

    return () => {
      cancelled = true
    }
  }, [selectedEntityId])

  if (!selectedEntityId) {
    return (
      <div className="evidence-panel evidence-panel-empty">
        <MousePointerClick size={26} />
        Select a node to see its evidence trail.
      </div>
    )
  }

  return (
    <div className="evidence-panel">
      <h3>
        <FileSearch size={15} />
        Evidence — {selectedEntityId}
      </h3>
      {state.status === 'loading' && (
        <p className="evidence-status">
          <span className="spinner" />
          Loading...
        </p>
      )}
      {state.status === 'pending' && (
        <p className="evidence-status evidence-pending">
          <Clock size={14} />
          {state.message}
        </p>
      )}
      {state.status === 'error' && (
        <p className="evidence-status evidence-error">
          <AlertCircle size={14} />
          {state.message}
        </p>
      )}
      {state.status === 'ready' && state.evidence.length === 0 && (
        <p className="evidence-status">No supporting documents on file for this entity.</p>
      )}
      {state.status === 'ready' && state.evidence.length > 0 && (
        <ul className="evidence-list">
          {state.evidence.map((doc) => (
            <li key={doc.id} className="evidence-item">
              <div className="evidence-item-type">
                <FileText size={12} />
                {doc.document_type}
              </div>
              <div className="evidence-item-text">{doc.raw_text}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
