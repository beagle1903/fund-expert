import { Briefcase, SlidersHorizontal } from 'lucide-react';
import {
  DIVERSIFICATION_OPTIONS,
  getDiversificationCap,
} from '../config.js';

const PRIORITIES = ['low', 'medium', 'high'];

function SelectControl({ label, name, onChange, options, value }) {
  return (
    <div className="control-group">
      <label htmlFor={name}>{label}</label>
      <select id={name} name={name} value={value ?? ''} onChange={onChange}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function ControlPanel({
  config,
  founders,
  loading,
  onChange,
  onEditRules,
  onSubmit,
}) {
  const priorityOptions = PRIORITIES.map((value) => ({
    value,
    label: value[0].toUpperCase() + value.slice(1),
  }));

  return (
    <aside className="glass-panel">
      <h2 className="app-title text-gradient">
        <Briefcase size={24} /> Fundexpert
      </h2>

      <form onSubmit={onSubmit}>
        <SelectControl
          label="Universe"
          name="universe"
          value={config.universe}
          onChange={onChange}
          options={[
            { value: 'tefas', label: 'TEFAS' },
            { value: 'befas', label: 'BEFAS' },
          ]}
        />
        <SelectControl
          label="Founder (Kurucu)"
          name="founder"
          value={config.founder}
          onChange={onChange}
          options={[
            { value: '', label: 'All founders' },
            ...founders.map((founder) => ({
              value: founder.name,
              label: `${founder.name} (${founder.fund_count})`,
            })),
          ]}
        />
        <SelectControl
          label="Risk Level"
          name="risk_level"
          value={config.risk_level}
          onChange={onChange}
          options={priorityOptions}
        />
        <SelectControl
          label="Horizon"
          name="horizon"
          value={config.horizon}
          onChange={onChange}
          options={[
            { value: 'short', label: 'Short' },
            { value: 'medium', label: 'Medium' },
            { value: 'long', label: 'Long' },
          ]}
        />
        <SelectControl
          label="Volume Priority"
          name="volume_priority"
          value={config.volume_priority}
          onChange={onChange}
          options={priorityOptions}
        />
        <SelectControl
          label="Fee Priority"
          name="fee_priority"
          value={config.fee_priority}
          onChange={onChange}
          options={priorityOptions}
        />
        <SelectControl
          label="Momentum Priority"
          name="momentum_priority"
          value={config.momentum_priority}
          onChange={onChange}
          options={priorityOptions}
        />

        <div className="control-group">
          <label htmlFor="n">Portfolio Size (N): {config.n}</label>
          <input
            id="n"
            type="range"
            name="n"
            min="3"
            max="20"
            value={config.n}
            onChange={onChange}
          />
        </div>

        <SelectControl
          label="Diversification"
          name="diversification_mode"
          value={config.diversification_mode}
          onChange={onChange}
          options={DIVERSIFICATION_OPTIONS}
        />
        <p className="control-help" aria-live="polite">
          Maximum {getDiversificationCap(config.n, config.diversification_mode)} funds
          per strategy or named sector.
        </p>

        <div className="control-group checkbox-control">
          <input
            type="checkbox"
            name="news_enabled"
            id="news_enabled"
            checked={config.news_enabled}
            onChange={onChange}
          />
          <label htmlFor="news_enabled">Enable News Pass</label>
        </div>

        <div className="control-group checkbox-control">
          <input
            type="checkbox"
            name="refresh_data"
            id="refresh_data"
            checked={config.refresh_data}
            onChange={onChange}
          />
          <label htmlFor="refresh_data">
            Refresh stale TEFAS data before generating
          </label>
        </div>

        <button type="submit" className="btn-primary" disabled={loading}>
          {loading
            ? config.refresh_data
              ? 'Refreshing & Generating…'
              : 'Generating…'
            : 'Generate Portfolio'}
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
