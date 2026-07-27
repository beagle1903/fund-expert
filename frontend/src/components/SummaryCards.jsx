import { Activity, CalendarClock, Newspaper, ShieldAlert } from 'lucide-react';
import { formatExportedAt } from '../utils/format.js';

export default function SummaryCards({ header, newsMeta, snapshot }) {
  return (
    <div className="summary-cards">
      <div className="glass-panel stat-card">
        <Activity size={24} color="var(--accent-primary)" />
        <div className="stat-value">
          {header.candidate_kept} /{' '}
          {header.founder
            ? header.candidate_after_founder
            : header.candidate_total}
        </div>
        <div className="stat-label">Funds Evaluated</div>
      </div>
      <div className="glass-panel stat-card">
        <ShieldAlert size={24} color="var(--warning)" />
        <div className="stat-value">{header.risk_level.toUpperCase()}</div>
        <div className="stat-label">Target Risk</div>
      </div>
      <div className="glass-panel stat-card">
        <Newspaper
          size={24}
          color={newsMeta.enabled ? 'var(--danger)' : 'var(--text-secondary)'}
        />
        <div className="stat-value">
          {newsMeta.enabled ? newsMeta.total_hits : 'OFF'}
        </div>
        <div className="stat-label">News Penalties</div>
      </div>
      <div className="glass-panel stat-card">
        <CalendarClock size={24} color="var(--accent-primary)" />
        <time className="stat-value stat-value-date" dateTime={snapshot.exported_at}>
          {formatExportedAt(snapshot.exported_at)}
        </time>
        <div className="stat-label">Data Exported · {snapshot.source}</div>
      </div>
    </div>
  );
}
