import { RotateCcw, Save, Settings2, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getFounders } from '../api/fundexpert.js';
import {
  DEFAULT_CONFIG,
  DIVERSIFICATION_OPTIONS,
  HORIZON_OPTIONS,
  PRIORITY_OPTIONS,
  UNIVERSE_OPTIONS,
  getDiversificationCap,
} from '../config.js';

function SelectField({ label, name, onChange, options, value }) {
  return (
    <div className="settings-field">
      <label htmlFor={`settings-${name}`}>{label}</label>
      <select
        id={`settings-${name}`}
        name={name}
        value={value ?? ''}
        onChange={onChange}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function getOptionLabel(options, value) {
  return options.find((option) => option.value === value)?.label ?? value;
}

export default function PortfolioSettings({
  config,
  founders,
  onApply,
  onClose,
}) {
  const [draftConfig, setDraftConfig] = useState(() => ({ ...config }));
  const [founderOptions, setFounderOptions] = useState(founders);
  const [founderLoading, setFounderLoading] = useState(false);
  const [founderError, setFounderError] = useState(null);

  useEffect(() => {
    if (draftConfig.universe === config.universe) {
      setFounderOptions(founders);
      setFounderError(null);
      return undefined;
    }

    const controller = new AbortController();
    setFounderLoading(true);
    setFounderError(null);
    getFounders(draftConfig.universe, { signal: controller.signal })
      .then(setFounderOptions)
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') {
          setFounderOptions([]);
          setFounderError('Founder options could not be loaded yet.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setFounderLoading(false);
        }
      });

    return () => controller.abort();
  }, [config.universe, draftConfig.universe, founders]);

  const handleChange = (event) => {
    const { checked, name, type, value } = event.target;
    const nextValue =
      type === 'checkbox'
        ? checked
        : type === 'range'
          ? Number(value)
          : name === 'founder' && value === ''
            ? null
            : value;

    setDraftConfig((previous) => {
      if (name === 'universe') {
        return { ...previous, universe: nextValue, founder: null };
      }
      return { ...previous, [name]: nextValue };
    });
  };

  const handleReset = () => {
    setDraftConfig({ ...DEFAULT_CONFIG });
  };

  const handleApply = () => {
    onApply({ ...draftConfig });
  };

  const cap = getDiversificationCap(
    draftConfig.n,
    draftConfig.diversification_mode,
  );

  return (
    <div className="settings-modal-backdrop" role="presentation">
      <section
        className="glass-panel settings-editor"
        role="dialog"
        aria-modal="true"
        aria-labelledby="portfolio-settings-title"
      >
        <header className="settings-editor-header">
          <div>
            <p className="settings-eyebrow">
              <Settings2 size={16} /> Portfolio profile
            </p>
            <h2 id="portfolio-settings-title">Web Run Settings</h2>
            <p>
              Configure this dashboard's next generation. These fields mirror{' '}
              <code>DEFAULT_CONFIG</code> in <code>config.js</code> and do not alter
              the build plugin profile.
            </p>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Close web run settings"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </header>

        <div className="settings-summary" aria-label="Draft settings summary">
          <div>
            <span>Target funds</span>
            <strong>{draftConfig.n}</strong>
          </div>
          <div>
            <span>Universe</span>
            <strong>{draftConfig.universe.toUpperCase()}</strong>
          </div>
          <div>
            <span>Risk / horizon</span>
            <strong>
              {getOptionLabel(PRIORITY_OPTIONS, draftConfig.risk_level)} /{' '}
              {getOptionLabel(HORIZON_OPTIONS, draftConfig.horizon)}
            </strong>
          </div>
          <div>
            <span>Diversification cap</span>
            <strong>{cap} per group</strong>
          </div>
        </div>

        <div className="settings-editor-body">
          <section className="settings-section" aria-labelledby="settings-scope-title">
            <div className="settings-section-heading">
              <div>
                <h3 id="settings-scope-title">Scope</h3>
                <p>Choose the fund universe and optional portfolio manager.</p>
              </div>
            </div>
            <div className="settings-grid settings-grid-two">
              <SelectField
                label="Universe"
                name="universe"
                value={draftConfig.universe}
                onChange={handleChange}
                options={UNIVERSE_OPTIONS}
              />
              <SelectField
                label="Founder (Kurucu)"
                name="founder"
                value={draftConfig.founder}
                onChange={handleChange}
                options={[
                  { value: '', label: 'All founders' },
                  ...founderOptions.map((founder) => ({
                    value: founder.name,
                    label: `${founder.name} (${founder.fund_count})`,
                  })),
                ]}
              />
            </div>
            {founderLoading && (
              <p className="settings-inline-note" role="status">
                Loading founder options…
              </p>
            )}
            {founderError && <p className="settings-inline-error">{founderError}</p>}
          </section>

          <section className="settings-section" aria-labelledby="settings-profile-title">
            <div className="settings-section-heading">
              <div>
                <h3 id="settings-profile-title">Risk profile</h3>
                <p>Set the time horizon and how much risk the score can tolerate.</p>
              </div>
            </div>
            <div className="settings-grid settings-grid-two">
              <SelectField
                label="Risk level"
                name="risk_level"
                value={draftConfig.risk_level}
                onChange={handleChange}
                options={PRIORITY_OPTIONS}
              />
              <SelectField
                label="Horizon"
                name="horizon"
                value={draftConfig.horizon}
                onChange={handleChange}
                options={HORIZON_OPTIONS}
              />
            </div>
          </section>

          <section className="settings-section" aria-labelledby="settings-priorities-title">
            <div className="settings-section-heading">
              <div>
                <h3 id="settings-priorities-title">Scoring priorities</h3>
                <p>Choose the relative emphasis for volume, fees, and momentum.</p>
              </div>
            </div>
            <div className="settings-grid settings-grid-three">
              <SelectField
                label="Volume"
                name="volume_priority"
                value={draftConfig.volume_priority}
                onChange={handleChange}
                options={PRIORITY_OPTIONS}
              />
              <SelectField
                label="Fees"
                name="fee_priority"
                value={draftConfig.fee_priority}
                onChange={handleChange}
                options={PRIORITY_OPTIONS}
              />
              <SelectField
                label="Momentum"
                name="momentum_priority"
                value={draftConfig.momentum_priority}
                onChange={handleChange}
                options={PRIORITY_OPTIONS}
              />
            </div>
          </section>

          <section className="settings-section" aria-labelledby="settings-selection-title">
            <div className="settings-section-heading">
              <div>
                <h3 id="settings-selection-title">Portfolio shape</h3>
                <p>Define the target number of funds and the diversification guardrail.</p>
              </div>
            </div>
            <div className="settings-grid settings-grid-two">
              <div className="settings-field settings-range-field">
                <div className="settings-range-label">
                  <label htmlFor="settings-n">Portfolio Size (N)</label>
                  <output htmlFor="settings-n">{draftConfig.n} funds</output>
                </div>
                <input
                  id="settings-n"
                  type="range"
                  name="n"
                  min="3"
                  max="20"
                  value={draftConfig.n}
                  onChange={handleChange}
                />
                <div className="settings-range-scale" aria-hidden="true">
                  <span>3</span>
                  <span>20</span>
                </div>
              </div>
              <div>
                <SelectField
                  label="Diversification"
                  name="diversification_mode"
                  value={draftConfig.diversification_mode}
                  onChange={handleChange}
                  options={DIVERSIFICATION_OPTIONS}
                />
                <p className="settings-inline-note">
                  Maximum {cap} funds per strategy or named sector.
                </p>
              </div>
            </div>
          </section>

          <section className="settings-section" aria-labelledby="settings-passes-title">
            <div className="settings-section-heading">
              <div>
                <h3 id="settings-passes-title">Optional passes</h3>
                <p>Choose whether generation should run the news and data-refresh passes.</p>
              </div>
            </div>
            <div className="settings-check-grid">
              <label className="settings-checkbox" htmlFor="settings-news_enabled">
                <input
                  type="checkbox"
                  id="settings-news_enabled"
                  name="news_enabled"
                  checked={draftConfig.news_enabled}
                  onChange={handleChange}
                />
                <span>
                  <strong>Enable News Pass</strong>
                  <small>Penalize selected funds with recent negative-news hits.</small>
                </span>
              </label>
              <label className="settings-checkbox" htmlFor="settings-refresh_data">
                <input
                  type="checkbox"
                  id="settings-refresh_data"
                  name="refresh_data"
                  checked={draftConfig.refresh_data}
                  onChange={handleChange}
                />
                <span>
                  <strong>Refresh stale TEFAS data</strong>
                  <small>Refresh before generating when the local snapshot is stale.</small>
                </span>
              </label>
            </div>
          </section>
        </div>

        <footer className="settings-editor-footer">
          <span>Changes apply to the next run; source defaults remain in config.js.</span>
          <div>
            <button type="button" className="btn-secondary compact" onClick={handleReset}>
              <RotateCcw size={16} /> Reset defaults
            </button>
            <button type="button" className="btn-secondary compact" onClick={onClose}>
              Cancel
            </button>
            <button type="button" className="btn-primary compact" onClick={handleApply}>
              <Save size={16} /> Apply settings
            </button>
          </div>
        </footer>
      </section>
    </div>
  );
}
