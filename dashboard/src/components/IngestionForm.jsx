/**
 * dashboard/src/components/IngestionForm.jsx
 *
 * Submits a new source document (FIR, CDR, financial record, etc.) to
 * api/routes/ingestion.py for the currently-selected case. Disabled
 * until a case is selected, since every document needs a case_id.
 */

import { AlertCircle, Info, Upload } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/client'
import { useToast } from './Toast'

const DOCUMENT_TYPES = ['fir', 'cdr', 'financial', 'surveillance', 'social', 'criminal_history', 'intel']

export default function IngestionForm({ caseId, onIngested }) {
  const [documentType, setDocumentType] = useState(DOCUMENT_TYPES[0])
  const [rawText, setRawText] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const showToast = useToast()

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const result = await api.ingest({
        id: crypto.randomUUID(),
        document_type: documentType,
        raw_text: rawText,
        case_id: caseId,
      })
      showToast(result.detail || `Document ${result.status}.`, 'success')
      setRawText('')
      onIngested?.(result)
    } catch (err) {
      setError(err.message)
      showToast(err.message, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="ingestion-form" onSubmit={handleSubmit}>
      <h3>
        <Upload size={14} />
        Ingest Document
      </h3>
      <label>
        Document type
        <select value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
          {DOCUMENT_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>
      <label>
        Raw text
        <textarea value={rawText} onChange={(e) => setRawText(e.target.value)} rows={4} required />
      </label>
      <button type="submit" disabled={submitting || !caseId}>
        {submitting && <span className="spinner" style={{ borderTopColor: 'white', borderColor: 'rgba(255,255,255,0.35)' }} />}
        {submitting ? 'Submitting...' : 'Ingest'}
      </button>
      {!caseId && (
        <p className="ingestion-hint">
          <Info size={13} />
          Select a case first.
        </p>
      )}
      {error && (
        <p className="ingestion-error">
          <AlertCircle size={13} />
          {error}
        </p>
      )}
    </form>
  )
}
