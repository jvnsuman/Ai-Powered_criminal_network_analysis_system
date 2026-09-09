/**
 * dashboard/src/api/client.js
 *
 * Thin fetch wrapper around the FastAPI backend (api/main.py). Handles
 * the auth token transparently and turns HTTP errors into JS Error
 * objects components can branch on — in particular err.pending (a 501:
 * the requested pipeline step, e.g. graph.build, isn't implemented
 * yet) versus a real error.
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

  /** Fetch a case's graph (currently 501 until graph.build exists — see App.jsx's sample-data fallback). */
  queryCase(caseId) {
    return request(`/query/${encodeURIComponent(caseId)}`)
  },

  /** Fetch the evidence trail for a selected entity. */
  getEvidence(entityId) {
    return request(`/evidence/${encodeURIComponent(entityId)}`)
  },
}
