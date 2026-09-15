/**
 * dashboard/src/components/ErrorBoundary.jsx
 *
 * Catches render/lifecycle errors thrown anywhere in its subtree and
 * shows an in-place fallback instead of letting the error propagate
 * up and unmount the whole app to a blank screen (React's default
 * behavior for an uncaught error with no boundary above it).
 *
 * This doesn't fix bugs — it contains them. Three separate pages
 * (DataSources, Reports, Settings) each blanked the entire app from a
 * single missing method on the api client; with this in place, the
 * same class of bug would instead show "Something went wrong" in
 * that one page's content area, sidebar/topbar/session still intact.
 *
 * Must be a class component: error boundaries are one of the few
 * remaining React APIs with no hooks equivalent (componentDidCatch /
 * getDerivedStateFromError have no useX() counterpart as of React 18).
 *
 * Usage: wrap the thing that might throw, and pass a `resetKey` that
 * changes when the user could plausibly retry (e.g. the current page
 * name) — changing that key remounts the boundary, clearing the
 * tripped state so navigating away and back tries rendering fresh
 * rather than showing the same stale fallback forever.
 *
 *   <ErrorBoundary resetKey={activePage} label={activePage}>
 *     {renderPage()}
 *   </ErrorBoundary>
 */

import { AlertTriangle, RotateCcw } from 'lucide-react'
import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    // Real errors still go to the console with their full stack /
    // component trace, same as an uncaught error would — this boundary
    // changes what the USER sees, not what gets logged for debugging.
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught an error:', error, info?.componentStack)
  }

  componentDidUpdate(prevProps) {
    // Clear the tripped state when resetKey changes (e.g. the user
    // navigated to a different page) so the fallback doesn't persist
    // once we're rendering something unrelated to what actually broke.
    if (this.state.error && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ error: null })
    }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="empty-state-panel">
          <AlertTriangle size={30} />
          <h3>Something went wrong{this.props.label ? ` on the ${this.props.label} page` : ''}.</h3>
          <p>
            {this.state.error.message || 'An unexpected error occurred.'}
            {' '}The rest of the app is unaffected — try again, or switch to a different page from the sidebar.
          </p>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => this.setState({ error: null })}
          >
            <RotateCcw size={14} />
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}