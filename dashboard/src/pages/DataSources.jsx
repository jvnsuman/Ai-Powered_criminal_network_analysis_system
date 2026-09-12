/**
 * pages/DataSources.jsx
 *
 * Data source management page. Per-source record counts and
 * last-updated timestamps now come from a real endpoint
 * (GET /ingest/{case_id}/summary, backed by db.repository's
 * get_document_summary_for_case) rather than being fabricated —
 * a type only shows a count once something's actually been
 * ingested under it.
 */

import { AlertCircle, Database, FileText, MessageSquare, Radio, Scale, ScrollText, Smartphone } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import IngestionForm from '../components/IngestionForm'

// Mirrors schema.entities.VALID_DOCUMENT_TYPES exactly.
const SOURCE_TYPES = [
  { key: 'fir', label: 'FIRs & Police Reports', icon: ScrollText },
  { key: 'cdr', label: 'CDRs', icon: Smartphone },
  { key: 'financial', label: 'Financial Transactions', icon: Scale },
  { key: 'surveillance', label: 'Surveillance Reports', icon: Radio },
  { key: 'social', label: 'Social Media Intelligence', icon: MessageSquare },
  { key: 'criminal_history', label: 'Criminal History Database', icon: FileText },
  { key: 'intel', label: 'Intelligence Agency Reports', icon: Database },
]

function formatTimestamp(iso) {
  if (!iso) return null
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

export default function DataSources({ selectedCaseId }) {
  const [summary, setSummary] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const refresh = useCallback(() => {
    if (!selectedCaseId) {
      setSummary({})
      return
    }
    setLoading(true)
    setError(null)
    api
      .getDocumentSummary(selectedCaseId)
      .then((data) => {
        const byType = {}
        data.sources.forEach((s) => {
          byType[s.document_type] = s
        })
        setSummary(byType)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [selectedCaseId])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <div className="page-sources">
      <h1>Data Sources</h1>
      <p className="page-sub">Manage and monitor your data sources.</p>

      {!selectedCaseId && (
        <div className="notice-banner">
          <AlertCircle size={15} />
          Select a case to see its ingested document counts.
        </div>
      )}
      {error && (
        <div className="notice-banner">
          <AlertCircle size={15} />
          {error}
        </div>
      )}

      <div className="sources-grid">
        {SOURCE_TYPES.map(({ key, label, icon: Icon }) => {
          const entry = summary[key]
          return (
            <div className="panel source-card" key={key}>
              <div className="source-card-icon">
                <Icon size={18} />
              </div>
              <div className="source-card-label">{label}</div>
              {entry ? (
                <>
                  <span className="source-card-count">{entry.count} record{entry.count === 1 ? '' : 's'}</span>
                  <span className="source-card-status">Updated {formatTimestamp(entry.last_updated)}</span>
                </>
              ) : (
                <span className="source-card-status">{loading ? 'Loading...' : 'No documents ingested yet'}</span>
              )}
            </div>
          )
        })}
      </div>

      <div className="panel">
        <div className="panel-header">
          <h3>Ingest a Document</h3>
        </div>
        <IngestionForm caseId={selectedCaseId} onIngested={refresh} />
      </div>
    </div>
  )
}
