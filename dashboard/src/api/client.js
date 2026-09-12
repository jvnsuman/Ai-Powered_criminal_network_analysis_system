/**
 * dashboard/src/api/client.js
 *
 * Thin fetch wrapper around the FastAPI backend (api/main.py). Handles
 * the auth token transparently and turns HTTP errors into JS Error
 * objects components can branch on — in particular err.pending (a 501:
 * the requested pipeline step, e.g. graph.build, isn't implemented
 * yet) versus a real error.
 *
 * NOTE ON THIS FILE'S HISTORY: an earlier edit (adding createCase)
 * was made from an incomplete copy of this file and accidentally
 * dropped getAlerts/listCases/getEvidence/generateReport/
 * downloadReport/updateSettings, breaking AlertsFeed, CaseSelector,
 * EvidencePanel, Reports, and Settings. Those methods have been
 * restored below based on their call sites (Reports.jsx, Settings.jsx,
 * AlertsFeed.jsx, CaseSelector.jsx, EvidencePanel.jsx). If anything
 * still breaks with "api.xxx is not a function", it means another
 * method used somewhere wasn't caught here — grep the dashboard for
 * `api.` calls and compare against the methods below.
 */

const BASE_URL = '/api'
const TOKEN_KEY = 'cna_auth_token'

/** Read the current session token from localStorage, or null. */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

/** Store (or clear, if token is falsy) the session token. */
function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

/**
 * Make a request to the backend, attaching the auth token if present.
 * Resolves with the parsed JSON body on success; throws an Error with
 * .status and .pending set on failure.
 */
async function request(path, { method = 'GET', body, params } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let url = `${BASE_URL}${path}`
  if (params) url += `?${new URLSearchParams(params).toString()}`

  let res
  try {
    res = await fetch(url, {
      method,
      headers: body ? { ...headers, 'Content-Type': 'application/json' } : headers,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (networkErr) {
    const err = new Error('Could not reach the API — is the backend running?')
    err.status = 0
    err.pending = false
    throw err
  }

  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }

  if (!res.ok) {
    const err = new Error(data?.detail || `Request failed with status ${res.status}`)
    err.status = res.status
    err.pending = res.status === 501
    throw err
  }
  return data
}

/**
 * Like request(), but for endpoints that return a raw file (e.g. a
 * PDF/CSV report) rather than JSON. Triggers a normal browser
 * "Save As" download via a temporary <a> click, instead of resolving
 * with parsed data.
 */
async function requestFileDownload(path, { method = 'GET', body, filename } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let res
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: body ? { ...headers, 'Content-Type': 'application/json' } : headers,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (networkErr) {
    const err = new Error('Could not reach the API — is the backend running?')
    err.status = 0
    err.pending = false
    throw err
  }

  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`
    try {
      const data = await res.json()
      detail = data?.detail || detail
    } catch {
      /* body wasn't JSON (likely a real file stream on success path, or empty on error) */
    }
    const err = new Error(detail)
    err.status = res.status
    err.pending = res.status === 501
    throw err
  }

  const blob = await res.blob()
  const objectUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename || 'download'
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(objectUrl)
}

export const api = {
  /** Log in and persist the returned session token. */
  async login(badgeId, password) {
    const data = await request('/auth/login', {
      method: 'POST',
      body: { badge_id: badgeId, password },
    })
    setToken(data.token)
    return data
  },

  /** Invalidate the session server-side (best-effort) and clear it locally. */
  async logout() {
    const token = getToken()
    setToken(null)
    if (token) {
      try {
        await request('/auth/logout', { method: 'POST', params: { token } })
      } catch {
        /* token already invalid or server unreachable; client-side token is cleared regardless */
      }
    }
  },

  /** Submit a source document for ingestion (see api/routes/ingestion.py). */
  ingest(document) {
    return request('/ingest/', { method: 'POST', body: document })
  },

  /** List every case the logged-in user is authorized to see. */
  listCases() {
    return request('/cases/')
  },

  /** Create a new case with the given title (see api/routes/cases.py). */
  createCase(title) {
    return request('/cases/', { method: 'POST', body: { title } })
  },

  /** Fetch a case's graph (currently 501 until graph.build exists — see App.jsx's sample-data fallback). */
  queryCase(caseId) {
    return request(`/query/${encodeURIComponent(caseId)}`)
  },

  /** Fetch the evidence trail for a selected entity. */
  getEvidence(entityId) {
    return request(`/evidence/${encodeURIComponent(entityId)}`)
  },

  /**
   * Fetch flagged anomalies/alerts for a case (see api/routes/alerts.py,
   * a read-only wrapper around graph.analytics.detect_anomalies).
   * Returns { alerts: [{ id, title, detail, severity, tags }] }.
   */
  getAlerts(caseId) {
    return request(`/alerts/${encodeURIComponent(caseId)}`)
  },

  /**
   * Trigger report generation for a case, in the given format
   * (e.g. "pdf", "csv"). See dashboard/src/pages/Reports.jsx and
   * api/routes/reports.py's POST /{case_id}/generate.
   */
  generateReport(caseId, format) {
    return request(`/reports/${encodeURIComponent(caseId)}/generate`, {
      method: 'POST',
      body: { format },
    })
  },

  /**
   * Download a previously-generated report file. `report` is the
   * report object as listed in Reports.jsx — must carry an `id`,
   * which is used to build the download URL per
   * api/routes/reports.py's GET /{case_id}/{report_id}/download
   * (a GET with no body, not a POST). Triggers a browser download
   * rather than resolving with JSON.
   */
  downloadReport(caseId, report) {
    return requestFileDownload(
      `/reports/${encodeURIComponent(caseId)}/${encodeURIComponent(report.id)}/download`,
      {
        method: 'GET',
        filename: report?.filename || report?.name || `report-${report?.id || 'download'}`,
      }
    )
  },

  /**
   * Update user preferences/settings (see
   * dashboard/src/pages/Settings.jsx and api/routes/settings.py's
   * PUT /). Settings.jsx calls this with a single { [key]: value }
   * patch — settings.py's PUT handler needs to accept a partial
   * update (merge with existing) for that to behave as Settings.jsx
   * expects; confirm that's how it's implemented if this doesn't
   * behave as a patch. Returns { preferences: {...} }.
   */
  updateSettings(patch) {
    return request('/settings/', {
      method: 'PUT',
      body: patch,
    })
  },
}
