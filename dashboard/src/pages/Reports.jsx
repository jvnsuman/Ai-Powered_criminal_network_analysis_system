/**
 * pages/Reports.jsx
 *
 * Generates and lists real case reports via api/routes/reports.py.
 * Reports are a Markdown case summary or a CSV export of
 * per-document-type ingestion counts — built from whatever is
 * actually persisted for the case (case metadata + ingestion counts).
 *
 * No PDF option: that would need an extra rendering dependency
 * (reportlab/weasyprint) not in requirements.txt — see
 * api/routes/reports.py's docstring.
 */

import { AlertCircle, Download, FileText, Plus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { useToast } from '../components/Toast'

function formatTimestamp(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

export default function Reports({ selectedCaseId }) {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [format, setFormat] = useState('markdown')
  const [error, setError] = useState(null)
  const showToast = useToast()

  const refresh = useCallback(() => {
    if (!selectedCaseId) {
      setReports([])
      return
    }
    setLoading(true)
    setError(null)
    api
      .listReports(selectedCaseId)
      .then((data) => setReports(data.reports))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [selectedCaseId])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function handleGenerate() {
    if (!selectedCaseId) return
    setGenerating(true)
    try {
      await api.generateReport(selectedCaseId, format)
      showToast('Report generated.', 'success')
      refresh()
    } catch (err) {
      showToast(err.message, 'error')
    } finally {
      setGenerating(false)
    }
  }

  async function handleDownload(report) {
    try {
      await api.downloadReport(selectedCaseId, report)
    } catch (err) {
      showToast(err.message, 'error')
    }
  }

  return (
    <div className="page-reports">
      <div className="page-greeting">
        <div>
          <h1>Reports</h1>
          <p className="page-greeting-sub">Generate and export case summaries.</p>
        </div>
        <div className="graph-toolbar">
          <select className="entity-filter-select" value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="markdown">Markdown</option>
            <option value="csv">CSV</option>
          </select>
          <button type="button" className="btn-secondary" onClick={handleGenerate} disabled={!selectedCaseId || generating}>
            <Plus size={14} />
            {generating ? 'Generating...' : 'New report'}
          </button>
        </div>
      </div>

      {!selectedCaseId && (
        <div className="notice-banner">
          <AlertCircle size={15} />
          Select a case to generate or view its reports.
        </div>
      )}
      {error && (
        <div className="notice-banner">
          <AlertCircle size={15} />
          {error}
        </div>
      )}

      <div className="panel">
        {loading ? (
          <p className="panel-status">Loading reports...</p>
        ) : reports.length === 0 ? (
          <div className="empty-state-panel">
            <FileText size={28} />
            <h3>No reports yet</h3>
            <p>Generate one above — it&apos;s built from this case&apos;s real ingested document counts.</p>
          </div>
        ) : (
          <ul className="report-list">
            {reports.map((r) => (
              <li key={r.id} className="report-list-item">
                <div className="report-list-icon">
                  <FileText size={16} />
                </div>
                <div className="report-list-info">
                  <div className="report-list-title">{r.title}</div>
                  <div className="report-list-meta">
                    {formatTimestamp(r.created_at)} · {r.format.toUpperCase()}
                  </div>
                </div>
                <button type="button" className="report-list-download" onClick={() => handleDownload(r)} aria-label="Download report">
                  <Download size={16} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
