/**
 * Sidebar.jsx
 *
 * Left navigation rail: brand, primary nav, and the AI/ML attribution
 * strip at the bottom.
 *
 * IMPORTANT (per explicit request): the "Powered by AI/ML | Graph
 * Analytics | NLP" watermark from the original mockup screenshots is
 * intentionally NOT reproduced here. If you want it back, add a
 * <div className="sidebar-footer"> block with that text above
 * SidebarFooterWave.
 */

import {
  Database,
  FileText,
  LayoutDashboard,
  Search,
  Settings,
  Share2,
  ShieldCheck,
} from 'lucide-react'

const NAV_ITEMS = [
  { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { key: 'graph', label: 'Network Graph', icon: Share2 },
  { key: 'search', label: 'Search & Investigate', icon: Search },
  { key: 'sources', label: 'Data Sources', icon: Database },
  { key: 'reports', label: 'Reports', icon: FileText },
  { key: 'settings', label: 'Settings', icon: Settings },
]

export default function Sidebar({ activePage, onNavigate }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <ShieldCheck size={20} strokeWidth={2.3} />
        </div>
        <div>
          <div className="sidebar-brand-title">Criminal Network Analysis</div>
          <div className="sidebar-brand-subtitle">Smarter Insights, Safer Communities.</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            className={`sidebar-nav-item ${activePage === key ? 'active' : ''}`}
            onClick={() => onNavigate(key)}
          >
            <Icon size={17} strokeWidth={2.1} />
            {label}
          </button>
        ))}
      </nav>
    </aside>
  )
}
