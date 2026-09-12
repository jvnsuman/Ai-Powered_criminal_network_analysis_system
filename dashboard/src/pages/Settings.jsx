/**
 * pages/Settings.jsx
 *
 * User profile section shows real session data (name, role). Toggle
 * preferences are now real: backed by GET/PUT /settings/
 * (api/routes/settings.py), stored as a JSON blob on the user's row.
 * Each toggle flips its own key optimistically and reverts on error.
 */

import { AlertCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useToast } from '../components/Toast'

const TOGGLES = [
  { key: 'dark_mode', label: 'Dark mode' },
  { key: 'email_alerts', label: 'Email alerts' },
  { key: 'auto_refresh_graph', label: 'Auto-refresh graph' },
  { key: 'desktop_notifications', label: 'Desktop notifications' },
]

function initials(name) {
  if (!name) return '?'
  return name.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()
}

export default function SettingsPage({ session }) {
  const [preferences, setPreferences] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const showToast = useToast()

  useEffect(() => {
    api
      .getSettings()
      .then((data) => setPreferences(data.preferences))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  async function handleToggle(key) {
    const previous = preferences
    const next = { ...preferences, [key]: !preferences[key] }
    setPreferences(next) // optimistic
    try {
      const data = await api.updateSettings({ [key]: next[key] })
      setPreferences(data.preferences)
    } catch (err) {
      setPreferences(previous) // revert
      showToast(err.message, 'error')
    }
  }

  return (
    <div className="page-settings">
      <h1>Settings</h1>
      <p className="page-sub">Manage your system preferences and configurations.</p>

      <div className="settings-grid">
        <div className="panel">
          <div className="panel-header">
            <h3>User Profile</h3>
          </div>
          <div className="settings-profile">
            <span className="settings-profile-avatar">{initials(session?.name)}</span>
            <div>
              <div className="settings-profile-name">{session?.name}</div>
              <div className="settings-profile-role">{session?.role?.replace('_', ' ')}</div>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h3>System Preferences</h3>
          </div>
          {error && (
            <div className="notice-banner small">
              <AlertCircle size={13} />
              {error}
            </div>
          )}
          <ul className="settings-pref-list">
            {TOGGLES.map(({ key, label }) => (
              <li key={key}>
                <span>{label}</span>
                <button
                  type="button"
                  className={`settings-toggle ${preferences[key] ? 'on' : ''}`}
                  role="switch"
                  aria-checked={Boolean(preferences[key])}
                  disabled={loading}
                  onClick={() => handleToggle(key)}
                >
                  <span className="settings-toggle-knob" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
