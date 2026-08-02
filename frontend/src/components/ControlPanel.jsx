import { Bot, Briefcase, Settings2, SlidersHorizontal } from 'lucide-react';
import {
  DIVERSIFICATION_OPTIONS,
  HORIZON_OPTIONS,
  PRIORITY_OPTIONS,
  getDiversificationCap,
} from '../config.js';

function getLabel(options, value) {
  return options.find((option) => option.value === value)?.label ?? value;
}

export default function ControlPanel({
  config,
  loading,
  onEditBuildProfile,
  onEditRules,
  onEditSettings,
  onSubmit,
}) {
  const diversificationLabel = getLabel(
    DIVERSIFICATION_OPTIONS,
    config.diversification_mode,
  );

  return (
    <aside className="glass-panel control-panel">
      <header className="control-panel-header">
        <h2 className="app-title text-gradient">
          <Briefcase size={24} /> Fundexpert
        </h2>
        <p>Build a transparent, source-backed portfolio profile.</p>
      </header>

      <section className="profile-card" aria-label="Active portfolio profile">
        <div className="profile-card-header">
          <div>
            <p className="profile-eyebrow">Web generator</p>
            <h3>Current run settings</h3>
          </div>
          <span className="profile-status">Ready</span>
        </div>

        <div className="profile-grid">
          <div className="profile-item">
            <span>Universe</span>
            <strong>{config.universe.toUpperCase()}</strong>
          </div>
          <div className="profile-item">
            <span>Target funds</span>
            <strong>{config.n}</strong>
          </div>
          <div className="profile-item">
            <span>Risk / horizon</span>
            <strong>
              {getLabel(PRIORITY_OPTIONS, config.risk_level)} /{' '}
              {getLabel(HORIZON_OPTIONS, config.horizon)}
            </strong>
          </div>
          <div className="profile-item">
            <span>Diversification</span>
            <strong>{diversificationLabel}</strong>
          </div>
        </div>

        <p className="profile-help">
          Maximum {getDiversificationCap(config.n, config.diversification_mode)} funds
          per strategy or named sector.
        </p>
      </section>

      <form className="control-panel-actions" onSubmit={onSubmit}>
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading
            ? config.refresh_data
              ? 'Refreshing & Generating…'
              : 'Generating…'
            : 'Generate Portfolio'}
        </button>

        <button
          type="button"
          className="btn-secondary settings-launch-button"
          onClick={onEditBuildProfile}
        >
          <Bot size={18} /> Build Plugin Profile
        </button>

        <button
          type="button"
          className="btn-secondary settings-launch-button"
          onClick={onEditSettings}
        >
          <Settings2 size={18} /> Web Run Settings
        </button>

        <button
          type="button"
          className="btn-secondary rules-launch-button"
          onClick={onEditRules}
        >
          <SlidersHorizontal size={18} /> Edit Selection Rules
        </button>
      </form>
    </aside>
  );
}
