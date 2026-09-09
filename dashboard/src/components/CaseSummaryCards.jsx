/**
 * dashboard/src/components/CaseSummaryCards.jsx
 *
 * Top-of-dashboard summary metric cards: entities linked, key
 * influencers, flagged patterns.
 *
 * caseStats shape: { entitiesLinked, keyInfluencers, flaggedPatterns }
 * (see sampleData.js for the demo values, or a real caseData.stats
 * from api.queryCase once graph.build exists).
 */

import { AlertTriangle, Share2, TrendingUp } from 'lucide-react'

const CARD_DEFS = [
  { key: 'entitiesLinked', label: 'Entities Linked', icon: Share2, className: 'entities' },
  { key: 'keyInfluencers', label: 'Key Influencers', icon: TrendingUp, className: 'influencers' },
  { key: 'flaggedPatterns', label: 'Flagged Patterns', icon: AlertTriangle, className: 'patterns' },
]

export default function CaseSummaryCards({ caseStats }) {
  const stats = caseStats || {}
  return (
    <div className="case-summary-cards">
      {CARD_DEFS.map(({ key, label, icon: Icon, className }) => (
        <div className="summary-card" key={key}>
          <div className={`summary-card-icon ${className}`}>
            <Icon size={20} strokeWidth={2.2} />
          </div>
          <div>
            <div className="summary-card-value">{stats[key] ?? '—'}</div>
            <div className="summary-card-label">{label}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
