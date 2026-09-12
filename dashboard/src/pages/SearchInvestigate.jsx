/**
 * pages/SearchInvestigate.jsx
 *
 * Direct entity lookup, separate from the dashboard's graph-embedded
 * SearchBar (which filters/highlights within an already-loaded case
 * graph). This page is for jumping straight to an entity across
 * whatever case is loaded. "Recent Searches" persists to
 * localStorage only (client-side convenience) — there is no
 * search-history endpoint in api/routes/, so this is intentionally
 * NOT presented as synced across devices/sessions.
 */

import { Building2, Car, MapPin, Phone, Search, User } from 'lucide-react'
import { useEffect, useState } from 'react'

const CATEGORIES = [
  { key: 'person', label: 'Person', icon: User },
  { key: 'phone', label: 'Phone Number', icon: Phone },
  { key: 'location', label: 'Location', icon: MapPin },
  { key: 'vehicle', label: 'Vehicle', icon: Car },
  { key: 'organization', label: 'Organization', icon: Building2 },
]

const RECENT_KEY = 'cna_recent_searches'
const MAX_RECENT = 8

function loadRecent() {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]')
  } catch {
    return []
  }
}

export default function SearchInvestigate({ graphData, onSelectEntity }) {
  const [category, setCategory] = useState(null)
  const [query, setQuery] = useState('')
  const [recent, setRecent] = useState(loadRecent)
  const [results, setResults] = useState(null)

  useEffect(() => {
    localStorage.setItem(RECENT_KEY, JSON.stringify(recent))
  }, [recent])

  function runSearch(e) {
    e?.preventDefault()
    if (!query.trim()) return

    const matches = (graphData?.nodes || []).filter((n) => {
      const matchesCategory = !category || n.entity_type === category
      const matchesQuery = n.label.toLowerCase().includes(query.trim().toLowerCase())
      return matchesCategory && matchesQuery
    })
    setResults(matches)

    setRecent((prev) => {
      const entry = { term: query.trim(), category, timestamp: Date.now() }
      const deduped = prev.filter((r) => r.term.toLowerCase() !== entry.term.toLowerCase())
      return [entry, ...deduped].slice(0, MAX_RECENT)
    })
  }

  return (
    <div className="page-search">
      <h1>Search &amp; Investigate</h1>
      <p className="page-sub">Find and analyze entities, relationships, and patterns.</p>

      <form className="panel search-panel" onSubmit={runSearch}>
        <div className="search-panel-input">
          <Search size={16} />
          <input
            placeholder="Search by name, phone, or ID..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="btn-primary">Search</button>
        </div>
        <div className="search-panel-categories">
          {CATEGORIES.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              type="button"
              className={`category-chip ${category === key ? 'active' : ''}`}
              onClick={() => setCategory(category === key ? null : key)}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>
      </form>

      {results && (
        <div className="panel">
          <div className="panel-header"><h3>Results ({results.length})</h3></div>
          {results.length === 0 ? (
            <p className="panel-status">No matching entities in the current case graph.</p>
          ) : (
            <ul className="search-results-list">
              {results.map((r) => (
                <li key={r.id}>
                  <button type="button" className="search-result-item" onClick={() => onSelectEntity?.(r.id)}>
                    <span className={`type-pill tint-${r.entity_type === 'person' ? 'violet' : 'primary'}`}>
                      {r.entity_type}
                    </span>
                    {r.label}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="panel">
        <div className="panel-header"><h3>Recent Searches</h3></div>
        {recent.length === 0 ? (
          <p className="panel-status">Nothing searched yet this session.</p>
        ) : (
          <ul className="recent-search-list">
            {recent.map((r, i) => (
              <li key={i}>
                <span>{r.term}</span>
                <span className="recent-search-meta">{r.category || 'any type'}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
