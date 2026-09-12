/**
 * dashboard/src/components/AlertsFeed.jsx
 *
 * "Recent Alerts" panel on the dashboard home page — a thin, honest
 * view over api/routes/alerts.py, which itself is a read-only wrapper
 * around graph.analytics.detect_anomalies. No alert is fabricated
 * here or on the backend; an empty case honestly shows zero alerts.
 */

import { AlertTriangle, CheckCircle2, Clock } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function AlertsFeed({ caseId }) {
  const [state, setState] = useState({ status: 'idle', alerts: [] })

  useEffect(() => {
    if (!caseId) {
      setState({ status: 'idle', alerts: [] })
      return
    }
    let cancelled = false
    setState({ status: 'loading', alerts: [] })

    api
      .getAlerts(caseId)
      .then((data) => {
        if (cancelled) return
        setState({ status: 'ready', alerts: data.alerts || [] })
      })
      .catch((err) => {
        if (cancelled) return
        if (err.pending) {
          setState({ status: 'pending', alerts: [] })
        } else {
          setState({ status: 'error', alerts: [], message: err.message })
        }
      })

    return () => {
      cancelled = true
    }
  }, [caseId])

  return (
    <div className="panel alerts-feed">
      <div className="panel-header">
        <h3>
          <AlertTriangle size={15} />
          Recent Alerts
        </h3>
      </div>

      {state.status === 'loading' && <p className="panel-status"><span className="spinner" /> Loading...</p>}

      {state.status === 'pending' && (
        <p className="panel-status pending">
          <Clock size={14} />
          Alert analysis isn&apos;t connected to a live case yet.
        </p>
      )}

      {state.status === 'ready' && state.alerts.length === 0 && (
        <p className="panel-status success">
          <CheckCircle2 size={14} />
          No anomalies flagged for this case.
        </p>
      )}

      {state.status === 'ready' && state.alerts.length > 0 && (
        <ul className="alerts-list">
          {state.alerts.map((alert) => (
            <li key={alert.id} className={`alert-item severity-${alert.severity}`}>
              <div className="alert-item-title">{alert.title}</div>
              <div className="alert-item-detail">{alert.detail}</div>
              <div className="alert-item-tags">
                {alert.tags?.map((tag) => (
                  <span key={tag} className="alert-tag">
                    {tag}
                  </span>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
