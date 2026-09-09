/**
 * dashboard/src/App.jsx
 *
 * Top-level layout: login gate, case selector, and the four main
 * dashboard components (SearchBar, CaseSummaryCards, GraphCanvas,
 * EvidencePanel), plus the ingestion form.
 *
 * Real graph data comes from api.queryCase (api/routes/query.py).
 * While graph.build is [TODO] that call reports 501, so this falls
 * back to the clearly-labeled synthetic sample graph (sampleData.js)
 * — never silently presented as real case data.
 */

import { AlertTriangle, Network } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, getToken } from './api/client'
import { SAMPLE_GRAPH } from './sampleData'
import CaseSelector from './components/CaseSelector'
import CaseSummaryCards from './components/CaseSummaryCards'
import EvidencePanel from './components/EvidencePanel'
import GraphCanvas from './components/GraphCanvas'
import GraphSkeleton from './components/GraphSkeleton'
import IngestionForm from './components/IngestionForm'
import LoginForm from './components/LoginForm'
import SearchBar from './components/SearchBar'

function initials(name) {
  if (!name) return '?'
  return name.split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase()
}

export default function App() {
  const [session, setSession] = useState(null)
  const [selectedCaseId, setSelectedCaseId] = useState(null)
  const [caseData, setCaseData] = useState(null)
  const [caseLoading, setCaseLoading] = useState(false)
  const [usingSampleData, setUsingSampleData] = useState(false)
  const [loadError, setLoadError] = useState(null)
  const [selectedEntityId, setSelectedEntityId] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')

  // Restore a session from a previously-stored token so a page reload
  // doesn't force a fresh login.
  useEffect(() => {
    if (getToken()) setSession({ restored: true })
  }, [])

  // Whenever the selected case changes, try to load its real graph;
  // fall back to the sample graph if the pipeline isn't ready yet.
  useEffect(() => {
    if (!session || !selectedCaseId) return
    let cancelled = false
    setCaseLoading(true)
    setCaseData(null)

    api
      .queryCase(selectedCaseId)
      .then((data) => {
        if (cancelled) return
        setCaseData(data)
        setUsingSampleData(false)
        setLoadError(null)
      })
      .catch((err) => {
        if (cancelled) return
        if (err.pending) {
          setCaseData(SAMPLE_GRAPH)
          setUsingSampleData(true)
          setLoadError(null)
        } else {
          setLoadError(err.message)
        }
      })
      .finally(() => {
        if (!cancelled) setCaseLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [session, selectedCaseId])

  if (!session) {
    return (
      <div className="app-shell app-shell-centered">
        <LoginForm onLoggedIn={setSession} />
      </div>
    )
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-title">
          <div className="app-header-logo">
            <Network size={19} strokeWidth={2.4} />
          </div>
          <div>
            <h1>Criminal Network Analysis</h1>
            <div className="app-header-subtitle">Investigator Console</div>
          </div>
        </div>
        <div className="app-header-controls">
          <CaseSelector selectedCaseId={selectedCaseId} onSelectCase={setSelectedCaseId} />
          {session.name && (
            <div className="user-chip">
              <span className="user-chip-avatar">{initials(session.name)}</span>
              <div className="user-chip-text">
                <span className="user-chip-name">{session.name}</span>
                <span className="user-chip-role">{session.role?.replace('_', ' ')}</span>
              </div>
            </div>
          )}
          <button
            type="button"
            className="logout-button"
            onClick={() => {
              api.logout()
              setSession(null)
              setCaseData(null)
              setSelectedCaseId(null)
            }}
          >
            Sign out
          </button>
        </div>
      </header>

      {usingSampleData && (
        <div className="sample-data-banner">
          <AlertTriangle size={15} />
          Showing synthetic sample data — the live graph pipeline isn't connected yet.
        </div>
      )}
      {loadError && (
        <div className="error-banner">
          <AlertTriangle size={15} />
          {loadError}
        </div>
      )}

      <CaseSummaryCards caseStats={caseData?.stats} />

      <div className="app-body">
        <div className="app-main">
          <SearchBar onSearch={setSearchQuery} />
          {caseLoading ? (
            <GraphSkeleton />
          ) : (
            <GraphCanvas
              graphData={caseData}
              searchQuery={searchQuery}
              onNodeSelect={setSelectedEntityId}
            />
          )}
        </div>
        <div className="app-sidebar">
          <EvidencePanel selectedEntityId={selectedEntityId} />
          <IngestionForm caseId={selectedCaseId} />
        </div>
      </div>
    </div>
  )
}
