/**
 * dashboard/src/components/LoginForm.jsx
 *
 * Badge-ID/password login gate shown before the dashboard renders.
 * Every route in api/main.py requires a Bearer token, so this is what
 * collects it and hands the resulting session to App.jsx.
 */

import { AlertCircle, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/client'

export default function LoginForm({ onLoggedIn }) {
  const [badgeId, setBadgeId] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const session = await api.login(badgeId, password)
      onLoggedIn(session)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="login-form" onSubmit={handleSubmit}>
      <div className="login-form-icon">
        <ShieldCheck size={26} strokeWidth={2.2} />
      </div>
      <h2>Investigator Login</h2>
      <p className="login-form-subtitle">Sign in with your issued badge credentials.</p>
      <label>
        Badge ID
        <input value={badgeId} onChange={(e) => setBadgeId(e.target.value)} autoFocus autoComplete="username" />
      </label>
      <label>
        Password
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />
      </label>
      {error && (
        <p className="login-error">
          <AlertCircle size={15} />
          {error}
        </p>
      )}
      <button type="submit" disabled={submitting}>
        {submitting && <span className="spinner" style={{ borderTopColor: 'white', borderColor: 'rgba(255,255,255,0.35)' }} />}
        {submitting ? 'Signing in...' : 'Sign in'}
      </button>
      <p className="login-demo-hint">demo: INV001 / investigator123</p>
    </form>
  )
}
