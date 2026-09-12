/**
 * dashboard/src/components/CaseSelector.jsx
 *
 * Dropdown of every case the logged-in user is authorized to see
 * (api/routes/cases.py's GET /cases/, already role/agency-scoped
 * server-side), plus a "New Case" button that creates a case via
 * POST /cases/ and immediately selects it.
 *
 * The New Case button is intentionally simple (a single title prompt)
 * — it exists to unblock investigators who have no case to select yet,
 * not to replace a fuller "create case" form later.
 */

import { Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useToast } from './Toast'

export default function CaseSelector({ selectedCaseId, onSelectCase }) {
  const [cases, setCases] = useState([])
  const [error, setError] = useState(null)
  const [creating, setCreating] = useState(false)
  const showToast = useToast()

  function refreshCases(selectId) {
    return api
      .listCases()
      .then((data) => {
        const list = data.cases || []
        setCases(list)
        if (selectId) {
          onSelectCase(selectId)
        } else if (!selectedCaseId && list.length > 0) {
          onSelectCase(list[0].id)
        }
        return list
      })
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    refreshCases()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleCreateCase() {
    const title = window.prompt('Case title:')
    if (!title || !title.trim()) return

    setCreating(true)
    try {
      const created = await api.createCase(title.trim())
      await refreshCases(created.id)
      showToast(`Case "${created.title}" created.`, 'success')
    } catch (err) {
      showToast(err.message, 'error')
    } finally {
      setCreating(false)
    }
  }

  if (error) return <div className="case-selector case-selector-error">{error}</div>

  return (
    <div className="case-selector-group">
      <select
        className="case-selector"
        value={selectedCaseId || ''}
        onChange={(e) => onSelectCase(e.target.value)}
      >
        <option value="" disabled>
          {cases.length === 0 ? 'No cases yet' : 'Select a case'}
        </option>
        {cases.map((c) => (
          <option key={c.id} value={c.id}>
            {c.title}
          </option>
        ))}
      </select>
      <button
        type="button"
        className="new-case-button"
        onClick={handleCreateCase}
        disabled={creating}
        title="Create a new case"
      >
        <Plus size={15} />
        {creating ? 'Creating…' : 'New Case'}
      </button>
    </div>
  )
}
