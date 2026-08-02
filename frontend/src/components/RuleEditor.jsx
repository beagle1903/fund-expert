import { useEffect, useMemo, useState } from 'react';
import {
  ArrowDown,
  ArrowUp,
  Plus,
  Save,
  ShieldCheck,
  Trash2,
  X,
} from 'lucide-react';
import {
  getSelectionRules,
  updateSelectionRules,
} from '../api/fundexpert.js';

const TABS = [
  { id: 'bucket_rules', label: 'Strategies' },
  { id: 'sector_rules', label: 'Sectors' },
  { id: 'exclusion_rules', label: 'Exclusions' },
];

const CATEGORY_SUGGESTIONS = {
  bucket_rules: [
    'equity',
    'money_market',
    'precious_metals',
    'debt',
    'fund_of_funds',
    'index',
    'mixed',
    'other',
  ],
  sector_rules: [
    'tech',
    'health',
    'energy',
    'finance',
    'real_estate',
    'industrial',
    'metals',
    'chemicals',
    'consumer',
    'agriculture',
    'tourism',
    'telecom',
    'transport',
    'defense',
    'diversified',
  ],
};

const EMPTY_RULES = {
  bucket_rules: [],
  sector_rules: [],
  exclusion_rules: [],
};

function moveItem(items, index, offset) {
  const target = index + offset;
  if (target < 0 || target >= items.length) {
    return items;
  }
  const next = [...items];
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

function validateRules(rules) {
  for (const key of ['bucket_rules', 'sector_rules']) {
    const keywords = rules[key].map((rule) =>
      rule.keyword.trim().toLocaleLowerCase('tr-TR'),
    );
    if (rules[key].some((rule) => !rule.keyword.trim() || !rule.category.trim())) {
      return 'Every classification rule needs a keyword and category.';
    }
    if (new Set(keywords).size !== keywords.length) {
      return 'Keywords must be unique within each section.';
    }
    if (rules[key].some((rule) => !/^[a-z][a-z0-9_]*$/.test(rule.category.trim()))) {
      return 'Categories must use lower-case words separated by underscores.';
    }
  }
  const exclusions = rules.exclusion_rules.map((rule) =>
    rule.trim().toLocaleLowerCase('tr-TR'),
  );
  if (exclusions.some((rule) => !rule)) {
    return 'Exclusion keywords cannot be blank.';
  }
  if (new Set(exclusions).size !== exclusions.length) {
    return 'Exclusion keywords must be unique.';
  }
  return null;
}

export default function RuleEditor({ onClose, onSaved }) {
  const [activeTab, setActiveTab] = useState('bucket_rules');
  const [rules, setRules] = useState(EMPTY_RULES);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    getSelectionRules({ signal: controller.signal })
      .then(setRules)
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') {
          setError(requestError.message);
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  const counts = useMemo(
    () => Object.fromEntries(TABS.map((tab) => [tab.id, rules[tab.id].length])),
    [rules],
  );

  const updateRule = (index, field, value) => {
    setRules((previous) => ({
      ...previous,
      [activeTab]: previous[activeTab].map((rule, ruleIndex) =>
        ruleIndex === index ? { ...rule, [field]: value } : rule,
      ),
    }));
  };

  const removeRule = (index) => {
    setRules((previous) => ({
      ...previous,
      [activeTab]: previous[activeTab].filter((_, ruleIndex) => ruleIndex !== index),
    }));
  };

  const reorderRule = (index, offset) => {
    setRules((previous) => ({
      ...previous,
      [activeTab]: moveItem(previous[activeTab], index, offset),
    }));
  };

  const addRule = () => {
    const newRule =
      activeTab === 'exclusion_rules' ? '' : { keyword: '', category: '' };
    setRules((previous) => ({
      ...previous,
      [activeTab]: [...previous[activeTab], newRule],
    }));
  };

  const handleSave = async () => {
    const validationError = validateRules(rules);
    if (validationError) {
      setError(validationError);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const saved = await updateSelectionRules({
        bucket_rules: rules.bucket_rules.map((rule) => ({
          keyword: rule.keyword.trim(),
          category: rule.category.trim(),
        })),
        sector_rules: rules.sector_rules.map((rule) => ({
          keyword: rule.keyword.trim(),
          category: rule.category.trim(),
        })),
        exclusion_rules: rules.exclusion_rules.map((rule) => rule.trim()),
      });
      setRules(saved);
      onSaved(saved);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  };

  const activeRules = rules[activeTab];
  const isExclusionTab = activeTab === 'exclusion_rules';

  return (
    <div className="rules-modal-backdrop" role="presentation">
      <section
        className="glass-panel rules-editor"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rules-editor-title"
      >
        <header className="rules-editor-header">
          <div>
            <p className="rules-eyebrow">
              <ShieldCheck size={16} /> Safe configuration
            </p>
            <h2 id="rules-editor-title">Selection Rules</h2>
            <p>
              Match fund-name keywords to strategy and sector groups. Earlier
              rules have higher priority.
            </p>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Close selection rules"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </header>

        <nav className="rules-tabs" aria-label="Rule sections">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={activeTab === tab.id ? 'active' : ''}
              onClick={() => {
                setActiveTab(tab.id);
                setError(null);
              }}
            >
              {tab.label} <span>{counts[tab.id]}</span>
            </button>
          ))}
        </nav>

        {error && <div className="rules-error" role="alert">{error}</div>}

        <div className="rules-editor-body">
          {loading ? (
            <div className="rules-empty" role="status">Loading selection rules…</div>
          ) : (
            <>
              <div className="rules-list-header">
                <div>
                  <h3>{TABS.find((tab) => tab.id === activeTab)?.label}</h3>
                  <p>
                    {isExclusionTab
                      ? 'Funds containing these whole-word keywords are removed before scoring.'
                      : 'Matching is case-insensitive and treats the keyword as plain text.'}
                  </p>
                </div>
                <button type="button" className="btn-secondary compact" onClick={addRule}>
                  <Plus size={16} /> Add rule
                </button>
              </div>

              {activeRules.length === 0 ? (
                <div className="rules-empty">No rules in this section yet.</div>
              ) : (
                <div className="rules-list">
                  {activeRules.map((rule, index) => (
                    <div className="rule-row" key={`${activeTab}-${index}`}>
                      <span className="rule-priority" title="Match priority">
                        {index + 1}
                      </span>
                      {isExclusionTab ? (
                        <input
                          aria-label={`Exclusion keyword ${index + 1}`}
                          value={rule}
                          placeholder="e.g. OKS"
                          onChange={(event) => {
                            const value = event.target.value;
                            setRules((previous) => ({
                              ...previous,
                              exclusion_rules: previous.exclusion_rules.map(
                                (item, ruleIndex) => ruleIndex === index ? value : item,
                              ),
                            }));
                          }}
                        />
                      ) : (
                        <>
                          <input
                            aria-label={`${activeTab} keyword ${index + 1}`}
                            value={rule.keyword}
                            placeholder="Fund-name keyword"
                            onChange={(event) =>
                              updateRule(index, 'keyword', event.target.value)
                            }
                          />
                          <input
                            aria-label={`${activeTab} category ${index + 1}`}
                            list={`${activeTab}-category-options`}
                            value={rule.category}
                            placeholder="category_name"
                            onChange={(event) =>
                              updateRule(index, 'category', event.target.value)
                            }
                          />
                        </>
                      )}
                      <div className="rule-actions">
                        <button
                          type="button"
                          className="icon-button"
                          aria-label={`Move rule ${index + 1} up`}
                          disabled={index === 0}
                          onClick={() => reorderRule(index, -1)}
                        >
                          <ArrowUp size={16} />
                        </button>
                        <button
                          type="button"
                          className="icon-button"
                          aria-label={`Move rule ${index + 1} down`}
                          disabled={index === activeRules.length - 1}
                          onClick={() => reorderRule(index, 1)}
                        >
                          <ArrowDown size={16} />
                        </button>
                        <button
                          type="button"
                          className="icon-button danger"
                          aria-label={`Delete rule ${index + 1}`}
                          onClick={() => removeRule(index)}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {CATEGORY_SUGGESTIONS[activeTab] && (
          <datalist id={`${activeTab}-category-options`}>
            {CATEGORY_SUGGESTIONS[activeTab].map((category) => (
              <option key={category} value={category} />
            ))}
          </datalist>
        )}

        <footer className="rules-editor-footer">
          <span>Changes are saved atomically to fundexpert/rules.json.</span>
          <div>
            <button type="button" className="btn-secondary compact" onClick={onClose}>
              Cancel
            </button>
            <button
              type="button"
              className="btn-primary compact"
              disabled={loading || saving}
              onClick={handleSave}
            >
              <Save size={16} /> {saving ? 'Saving…' : 'Save & Rebuild'}
            </button>
          </div>
        </footer>
      </section>
    </div>
  );
}
