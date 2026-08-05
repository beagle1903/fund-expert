import {
  Bot,
  Check,
  RotateCcw,
  Save,
  ShieldCheck,
  X,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import {
  getBuildProfile,
  updateBuildProfile,
} from '../api/fundexpert.js';

const RISK_OPTIONS = [
  { value: 'low', label: 'Low', band: [1, 2, 3] },
  { value: 'medium', label: 'Medium', band: [3, 4, 5] },
  { value: 'medium_high', label: 'Medium high', band: [4, 5, 6] },
  { value: 'high', label: 'High', band: [5, 6, 7] },
];

const TABS = [
  { id: 'profile', label: 'Profile' },
  { id: 'scoring', label: 'Scoring & selection' },
  { id: 'audit', label: 'Market & audit' },
];

const METRIC_FIELDS = [
  { key: 'return', label: 'Return', help: 'Historical performance signal.' },
  { key: 'current_aum', label: 'Current AUM', help: 'Current fund size.' },
  { key: 'aum_growth', label: 'AUM growth', help: 'Growth in managed assets.' },
  { key: 'units_growth', label: 'Units growth', help: 'Growth in investor units.' },
  {
    key: 'management_fee',
    label: 'Management fee',
    help: 'Fee preference; zero disables it.',
  },
];

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function riskLabel(value) {
  return RISK_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

function updatePath(source, path, value) {
  const next = clone(source);
  let target = next;
  for (const segment of path.slice(0, -1)) {
    target = target[segment];
  }
  target[path.at(-1)] = value;
  return next;
}

function parseSourceIds(value) {
  return value
    .split(',')
    .map((source) => source.trim())
    .filter(Boolean);
}

function isFiniteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

function validateDraft(profile) {
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(profile.profile_id)) {
    return 'Profile ID must use lowercase letters, numbers, and hyphens.';
  }
  if (profile.allowed_risk_values.length === 0) {
    return 'Select at least one allowed risk value.';
  }
  if (
    !Number.isInteger(profile.holding_period_days) ||
    profile.holding_period_days < 1 ||
    profile.holding_period_days > 3650
  ) {
    return 'Holding period must be a whole number from 1 to 3650 days.';
  }
  if (
    !Number.isInteger(profile.fund_count) ||
    profile.fund_count < 1 ||
    profile.fund_count > 20
  ) {
    return 'Target fund count must be a whole number from 1 to 20.';
  }

  const weights = Object.values(profile.metric_weights);
  if (weights.some((value) => !isFiniteNumber(value) || value < 0)) {
    return 'Metric weights must be finite numbers of zero or greater.';
  }
  if (weights.reduce((sum, value) => sum + value, 0) <= 0) {
    return 'At least one metric weight must be greater than zero.';
  }
  if (
    !isFiniteNumber(profile.risk_penalty_weight) ||
    profile.risk_penalty_weight < 0
  ) {
    return 'Risk penalty must be a finite number of zero or greater.';
  }

  const { lower_quantile: lower, upper_quantile: upper } =
    profile.growth_winsorization;
  if (
    !isFiniteNumber(lower) ||
    !isFiniteNumber(upper) ||
    lower < 0 ||
    upper > 1 ||
    lower >= upper
  ) {
    return 'Growth limits must satisfy 0 ≤ lower < upper ≤ 1.';
  }

  const { max_per_sector: sectorCap, max_per_strategy: strategyCap } =
    profile.diversification;
  if (
    !Number.isInteger(strategyCap) ||
    !Number.isInteger(sectorCap) ||
    strategyCap < 1 ||
    strategyCap > 20 ||
    sectorCap < 1 ||
    sectorCap > 20
  ) {
    return 'Diversification caps must be whole numbers from 1 to 20.';
  }

  if (
    !Number.isInteger(profile.market_context.lookback_days) ||
    profile.market_context.lookback_days < 1 ||
    profile.market_context.lookback_days > 90
  ) {
    return 'Market lookback must be a whole number from 1 to 90 days.';
  }

  const { audit } = profile;
  if (
    !Number.isInteger(audit.max_data_age_days) ||
    audit.max_data_age_days < 0 ||
    audit.max_data_age_days > 365
  ) {
    return 'Maximum data age must be a whole number from 0 to 365 days.';
  }
  if (
    !isFiniteNumber(audit.max_single_fund_weight_pct) ||
    audit.max_single_fund_weight_pct < 0 ||
    audit.max_single_fund_weight_pct > 100
  ) {
    return 'Maximum single-fund weight must be between 0% and 100%.';
  }
  if (
    Math.floor(audit.max_single_fund_weight_pct / 5) * profile.fund_count <
    20
  ) {
    return 'Fund count and maximum weight cannot produce 100% in 5% steps.';
  }
  const [riskLow, riskHigh] = audit.target_weighted_risk_range;
  if (
    !isFiniteNumber(riskLow) ||
    !isFiniteNumber(riskHigh) ||
    riskLow < 1 ||
    riskLow > riskHigh ||
    riskHigh > 7
  ) {
    return 'Target weighted risk must be an ordered range from 1 to 7.';
  }
  return null;
}

function SelectField({ children, label, onChange, value }) {
  const id = `build-${label.toLowerCase().replaceAll(/[^a-z0-9]+/g, '-')}`;
  return (
    <div className="settings-field">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={onChange}>
        {children}
      </select>
    </div>
  );
}

function NumberField({ help, label, max, min, onChange, step = 1, value }) {
  const id = `build-${label.toLowerCase().replaceAll(/[^a-z0-9]+/g, '-')}`;
  return (
    <div className="settings-field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) =>
          onChange(event.target.value === '' ? '' : Number(event.target.value))
        }
      />
      {help && <small className="build-field-help">{help}</small>}
    </div>
  );
}

function ToggleCard({ checked, description, label, onChange }) {
  const id = `build-${label.toLowerCase().replaceAll(/[^a-z0-9]+/g, '-')}`;
  return (
    <label className="settings-checkbox" htmlFor={id}>
      <input id={id} type="checkbox" checked={checked} onChange={onChange} />
      <span>
        <strong>{label}</strong>
        <small>{description}</small>
      </span>
    </label>
  );
}

export default function BuildProfileSettings({ onClose }) {
  const [activeTab, setActiveTab] = useState('profile');
  const [draft, setDraft] = useState(null);
  const [loaded, setLoaded] = useState(null);
  const [sourceIdsText, setSourceIdsText] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    getBuildProfile({ signal: controller.signal })
      .then((response) => {
        setLoaded(response);
        setDraft(clone(response.profile));
        setSourceIdsText(response.profile.market_context.source_ids.join(', '));
      })
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') {
          setError(requestError.message);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [reloadKey]);

  const changePath = (path, value) => {
    setDraft((current) => updatePath(current, path, value));
    setError(null);
    setNotice(null);
  };

  const handleRiskTolerance = (event) => {
    const value = event.target.value;
    const band = RISK_OPTIONS.find((option) => option.value === value).band;
    setDraft((current) => ({
      ...current,
      risk_tolerance: value,
      allowed_risk_values: [...band],
    }));
    setError(null);
    setNotice(null);
  };

  const toggleRiskValue = (value) => {
    setDraft((current) => {
      const selected = current.allowed_risk_values.includes(value)
        ? current.allowed_risk_values.filter((item) => item !== value)
        : [...current.allowed_risk_values, value].sort((a, b) => a - b);
      return { ...current, allowed_risk_values: selected };
    });
    setError(null);
    setNotice(null);
  };

  const handleReset = () => {
    if (!loaded) return;
    setDraft(clone(loaded.profile));
    setSourceIdsText(loaded.profile.market_context.source_ids.join(', '));
    setError(null);
    setNotice('Unsaved changes were discarded.');
  };

  const handleSave = async () => {
    const profile = clone(draft);
    profile.market_context.source_ids = parseSourceIds(sourceIdsText);
    const validationError = validateDraft(profile);
    if (validationError) {
      setError(validationError);
      setNotice(null);
      return;
    }

    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const response = await updateBuildProfile(profile);
      setLoaded(response);
      setDraft(clone(response.profile));
      setSourceIdsText(response.profile.market_context.source_ids.join(', '));
      setNotice('Saved. The next build-portfolio plugin run will use this profile.');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-modal-backdrop" role="presentation">
      <section
        className="glass-panel settings-editor build-profile-editor"
        role="dialog"
        aria-modal="true"
        aria-labelledby="build-profile-title"
      >
        <header className="settings-editor-header">
          <div>
            <p className="settings-eyebrow">
              <Bot size={16} /> fund-expert:build-fund-portfolio
            </p>
            <h2 id="build-profile-title">Build Plugin Profile</h2>
            <p>
              Manage the saved inputs the plugin reads before it builds a
              portfolio. Saving here does not start a build.
            </p>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Close build plugin profile"
            onClick={onClose}
            disabled={saving}
          >
            <X size={20} />
          </button>
        </header>

        {draft && (
          <div className="settings-summary" aria-label="Build profile summary">
            <div>
              <span>Target funds</span>
              <strong>{draft.fund_count || '—'}</strong>
            </div>
            <div>
              <span>Universe</span>
              <strong>{draft.universe.toUpperCase()}</strong>
            </div>
            <div>
              <span>Risk profile</span>
              <strong>{riskLabel(draft.risk_tolerance)}</strong>
            </div>
            <div>
              <span>Holding period</span>
              <strong>{draft.holding_period_days || '—'} days</strong>
            </div>
          </div>
        )}

        <nav className="build-profile-tabs" aria-label="Profile sections" role="tablist">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              id={`build-tab-${tab.id}`}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              aria-controls={`build-panel-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="settings-editor-body build-profile-body">
          {loading && (
            <div className="build-profile-state" role="status">
              <Bot size={28} />
              <strong>Loading saved plugin profile…</strong>
            </div>
          )}

          {!loading && !draft && (
            <div className="build-profile-state" role="alert">
              <strong>Profile could not be loaded.</strong>
              <p>{error}</p>
              <button
                type="button"
                className="btn-secondary compact"
                onClick={() => setReloadKey((value) => value + 1)}
              >
                Try again
              </button>
            </div>
          )}

          {!loading && draft && activeTab === 'profile' && (
            <div
              id="build-panel-profile"
              role="tabpanel"
              aria-labelledby="build-tab-profile"
            >
              <section className="settings-section">
                <div className="settings-section-heading">
                  <div>
                    <h3>Identity & scope</h3>
                    <p>Name the profile and choose the fund universe.</p>
                  </div>
                  <span className="build-schema-badge">Schema {draft.schema_version}</span>
                </div>
                <div className="settings-grid settings-grid-two">
                  <div className="settings-field">
                    <label htmlFor="build-profile-id">Profile ID</label>
                    <input
                      id="build-profile-id"
                      type="text"
                      value={draft.profile_id}
                      onChange={(event) =>
                        changePath(['profile_id'], event.target.value)
                      }
                    />
                    <small className="build-field-help">
                      Lowercase letters, numbers, and hyphens.
                    </small>
                  </div>
                  <SelectField
                    label="Universe"
                    value={draft.universe}
                    onChange={(event) =>
                      changePath(['universe'], event.target.value)
                    }
                  >
                    <option value="tefas">TEFAS</option>
                    <option value="befas">BEFAS</option>
                  </SelectField>
                  <SelectField
                    label="Risk tolerance"
                    value={draft.risk_tolerance}
                    onChange={handleRiskTolerance}
                  >
                    {RISK_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </SelectField>
                  <NumberField
                    label="Holding period (days)"
                    min={1}
                    max={3650}
                    value={draft.holding_period_days}
                    onChange={(value) => changePath(['holding_period_days'], value)}
                  />
                  <NumberField
                    label="Target fund count"
                    min={1}
                    max={20}
                    value={draft.fund_count}
                    onChange={(value) => changePath(['fund_count'], value)}
                  />
                </div>
              </section>

              <section className="settings-section">
                <div className="settings-section-heading">
                  <div>
                    <h3>Allowed SRRI risk values</h3>
                    <p>
                      Changing risk tolerance selects its default band; customize
                      the values here if needed.
                    </p>
                  </div>
                </div>
                <div className="build-risk-grid" aria-label="Allowed SRRI risk values">
                  {[1, 2, 3, 4, 5, 6, 7].map((value) => {
                    const selected = draft.allowed_risk_values.includes(value);
                    return (
                      <button
                        key={value}
                        type="button"
                        className={selected ? 'selected' : ''}
                        aria-pressed={selected}
                        onClick={() => toggleRiskValue(value)}
                      >
                        {selected && <Check size={14} />}
                        {value}
                      </button>
                    );
                  })}
                </div>
              </section>

              <section className="settings-section">
                <div className="settings-section-heading">
                  <div>
                    <h3>Eligibility filters</h3>
                    <p>Remove candidates the plugin should not score.</p>
                  </div>
                </div>
                <div className="settings-check-grid">
                  <ToggleCard
                    label="Exclude missing risk"
                    description="Skip funds without an official SRRI value."
                    checked={draft.exclude_missing_risk}
                    onChange={(event) =>
                      changePath(['exclude_missing_risk'], event.target.checked)
                    }
                  />
                  <ToggleCard
                    label="Exclude qualified-investor funds"
                    description="Keep the result suitable for standard fund access."
                    checked={draft.exclude_qualified_investor_funds}
                    onChange={(event) =>
                      changePath(
                        ['exclude_qualified_investor_funds'],
                        event.target.checked,
                      )
                    }
                  />
                </div>
              </section>
            </div>
          )}

          {!loading && draft && activeTab === 'scoring' && (
            <div
              id="build-panel-scoring"
              role="tabpanel"
              aria-labelledby="build-tab-scoring"
            >
              <section className="settings-section">
                <div className="settings-section-heading">
                  <div>
                    <h3>Metric weights</h3>
                    <p>
                      Relative importance is normalized by the plugin; at least
                      one weight must be above zero.
                    </p>
                  </div>
                </div>
                <div className="settings-grid build-metric-grid">
                  {METRIC_FIELDS.map((field) => (
                    <NumberField
                      key={field.key}
                      label={field.label}
                      help={field.help}
                      min={0}
                      step={0.05}
                      value={draft.metric_weights[field.key]}
                      onChange={(value) =>
                        changePath(['metric_weights', field.key], value)
                      }
                    />
                  ))}
                  <NumberField
                    label="Risk penalty"
                    help="Penalty applied as SRRI rises."
                    min={0}
                    step={0.05}
                    value={draft.risk_penalty_weight}
                    onChange={(value) => changePath(['risk_penalty_weight'], value)}
                  />
                </div>
              </section>

              <section className="settings-section">
                <div className="settings-section-heading">
                  <div>
                    <h3>New-fund handling</h3>
                    <p>Define a new fund and how missing growth enters the score.</p>
                  </div>
                </div>
                <div className="settings-grid settings-grid-two">
                  <SelectField
                    label="New fund definition"
                    value={draft.new_fund_policy.definition}
                    onChange={(event) =>
                      changePath(
                        ['new_fund_policy', 'definition'],
                        event.target.value,
                      )
                    }
                  >
                    <option value="missing_1y_return">Missing 1-year return</option>
                    <option value="missing_3m_return">Missing 3-month return</option>
                  </SelectField>
                  <SelectField
                    label="Growth treatment"
                    value={draft.new_fund_policy.growth_treatment}
                    onChange={(event) =>
                      changePath(
                        ['new_fund_policy', 'growth_treatment'],
                        event.target.value,
                      )
                    }
                  >
                    <option value="neutral">Neutral</option>
                    <option value="observed">Observed values</option>
                  </SelectField>
                </div>
              </section>

              <section className="settings-section">
                <div className="settings-section-heading">
                  <div>
                    <h3>Growth limits & diversification</h3>
                    <p>Clip growth outliers, then cap repeated themes.</p>
                  </div>
                </div>
                <div className="settings-grid settings-grid-two">
                  <NumberField
                    label="Lower growth quantile"
                    min={0}
                    max={1}
                    step={0.01}
                    value={draft.growth_winsorization.lower_quantile}
                    onChange={(value) =>
                      changePath(
                        ['growth_winsorization', 'lower_quantile'],
                        value,
                      )
                    }
                  />
                  <NumberField
                    label="Upper growth quantile"
                    min={0}
                    max={1}
                    step={0.01}
                    value={draft.growth_winsorization.upper_quantile}
                    onChange={(value) =>
                      changePath(
                        ['growth_winsorization', 'upper_quantile'],
                        value,
                      )
                    }
                  />
                  <NumberField
                    label="Max funds per strategy"
                    min={1}
                    max={20}
                    value={draft.diversification.max_per_strategy}
                    onChange={(value) =>
                      changePath(['diversification', 'max_per_strategy'], value)
                    }
                  />
                  <NumberField
                    label="Max funds per sector"
                    min={1}
                    max={20}
                    value={draft.diversification.max_per_sector}
                    onChange={(value) =>
                      changePath(['diversification', 'max_per_sector'], value)
                    }
                  />
                </div>
              </section>
            </div>
          )}

          {!loading && draft && activeTab === 'audit' && (
            <div
              id="build-panel-audit"
              role="tabpanel"
              aria-labelledby="build-tab-audit"
            >
              <section className="settings-section">
                <div className="settings-section-heading">
                  <div>
                    <h3>Market context</h3>
                    <p>
                      Configure the qualitative market overlay used during the
                      plugin workflow.
                    </p>
                  </div>
                </div>
                <div className="settings-check-grid build-market-toggle">
                  <ToggleCard
                    label="Enable market context"
                    description="Include the configured recent market sources."
                    checked={draft.market_context.enabled}
                    onChange={(event) =>
                      changePath(
                        ['market_context', 'enabled'],
                        event.target.checked,
                      )
                    }
                  />
                </div>
                <div className="settings-grid settings-grid-two build-grid-spaced">
                  <NumberField
                    label="Market lookback (days)"
                    min={1}
                    max={90}
                    value={draft.market_context.lookback_days}
                    onChange={(value) =>
                      changePath(['market_context', 'lookback_days'], value)
                    }
                  />
                  <div className="settings-field">
                    <label htmlFor="build-selection-influence">
                      Selection influence
                    </label>
                    <input
                      id="build-selection-influence"
                      type="text"
                      value="Qualitative overlay"
                      readOnly
                      aria-readonly="true"
                    />
                    <small className="build-field-help">
                      Fixed by profile schema 1.0.
                    </small>
                  </div>
                  <div className="settings-field build-span-two">
                    <label htmlFor="build-market-sources">Market source IDs</label>
                    <input
                      id="build-market-sources"
                      type="text"
                      value={sourceIdsText}
                      placeholder="garanti_bbva_yatirim"
                      onChange={(event) => {
                        setSourceIdsText(event.target.value);
                        setError(null);
                        setNotice(null);
                      }}
                    />
                    <small className="build-field-help">
                      Separate multiple source IDs with commas.
                    </small>
                  </div>
                </div>
              </section>

              <section className="settings-section">
                <div className="settings-section-heading">
                  <div>
                    <h3>Audit guardrails</h3>
                    <p>Define freshness, concentration, and target risk checks.</p>
                  </div>
                  <ShieldCheck size={21} aria-hidden="true" />
                </div>
                <div className="settings-grid settings-grid-two">
                  <NumberField
                    label="Maximum data age (days)"
                    min={0}
                    max={365}
                    value={draft.audit.max_data_age_days}
                    onChange={(value) =>
                      changePath(['audit', 'max_data_age_days'], value)
                    }
                  />
                  <NumberField
                    label="Maximum single-fund weight (%)"
                    min={0}
                    max={100}
                    step={5}
                    value={draft.audit.max_single_fund_weight_pct}
                    onChange={(value) =>
                      changePath(
                        ['audit', 'max_single_fund_weight_pct'],
                        value,
                      )
                    }
                  />
                  <NumberField
                    label="Target weighted risk minimum"
                    min={1}
                    max={7}
                    step={0.1}
                    value={draft.audit.target_weighted_risk_range[0]}
                    onChange={(value) => {
                      const range = [...draft.audit.target_weighted_risk_range];
                      range[0] = value;
                      changePath(['audit', 'target_weighted_risk_range'], range);
                    }}
                  />
                  <NumberField
                    label="Target weighted risk maximum"
                    min={1}
                    max={7}
                    step={0.1}
                    value={draft.audit.target_weighted_risk_range[1]}
                    onChange={(value) => {
                      const range = [...draft.audit.target_weighted_risk_range];
                      range[1] = value;
                      changePath(['audit', 'target_weighted_risk_range'], range);
                    }}
                  />
                </div>
              </section>
            </div>
          )}
        </div>

        <div className="build-profile-feedback" aria-live="polite">
          {error && draft && <p className="build-feedback-error">{error}</p>}
          {notice && <p className="build-feedback-success">{notice}</p>}
        </div>

        <footer className="settings-editor-footer build-profile-footer">
          <span title={loaded?.profile_path}>
            {loaded
              ? `${loaded.source === 'saved' ? 'Saved profile' : 'Default template'} · ${loaded.profile_path}`
              : 'Profile location is loading…'}
          </span>
          <div>
            <button
              type="button"
              className="btn-secondary compact"
              onClick={handleReset}
              disabled={!draft || saving}
            >
              <RotateCcw size={16} /> Discard edits
            </button>
            <button
              type="button"
              className="btn-secondary compact"
              onClick={onClose}
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn-primary compact"
              onClick={handleSave}
              disabled={!draft || saving}
            >
              <Save size={16} /> {saving ? 'Saving…' : 'Save plugin profile'}
            </button>
          </div>
        </footer>
      </section>
    </div>
  );
}
