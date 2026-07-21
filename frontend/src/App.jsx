import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, AlertTriangle, ShieldAlert, Newspaper, Briefcase } from 'lucide-react';

const COLORS = ['#66fcf1', '#45a29e', '#bd93f9', '#ffb86c', '#ff5555', '#50fa7b', '#f1fa8c'];

export default function App() {
  const [config, setConfig] = useState({
    universe: 'tefas',
    risk_level: 'medium',
    horizon: 'medium',
    volume_priority: 'medium',
    fee_priority: 'medium',
    momentum_priority: 'medium',
    n: 8,
    news_enabled: false
  });

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchPortfolio = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      if (!response.ok) {
        throw new Error(`Error: ${response.statusText}`);
      }
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolio();
  }, []); // Run once on mount

  const handleGenerate = (e) => {
    e.preventDefault();
    fetchPortfolio();
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setConfig(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  // Process data for charts
  let strategyData = [];
  if (data?.weighted) {
    const stratMap = {};
    data.weighted.forEach(fund => {
      const strat = fund.strategy || 'Other';
      stratMap[strat] = (stratMap[strat] || 0) + (fund.display_weight_pct);
    });
    strategyData = Object.keys(stratMap).map(k => ({ name: k, value: stratMap[k] }));
  }

  return (
    <div className="dashboard-container">
      {/* Left Sidebar - Control Panel */}
      <aside className="glass-panel">
        <h2 className="text-gradient" style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Briefcase size={24} /> Fundexpert
        </h2>
        
        <form onSubmit={handleGenerate}>
          <div className="control-group">
            <label>Universe</label>
            <select name="universe" value={config.universe} onChange={handleChange}>
              <option value="tefas">TEFAS</option>
              <option value="befas">BEFAS</option>
            </select>
          </div>

          <div className="control-group">
            <label>Risk Level</label>
            <select name="risk_level" value={config.risk_level} onChange={handleChange}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div className="control-group">
            <label>Horizon</label>
            <select name="horizon" value={config.horizon} onChange={handleChange}>
              <option value="short">Short</option>
              <option value="medium">Medium</option>
              <option value="long">Long</option>
            </select>
          </div>

          <div className="control-group">
            <label>Volume Priority</label>
            <select name="volume_priority" value={config.volume_priority} onChange={handleChange}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div className="control-group">
            <label>Fee Priority</label>
            <select name="fee_priority" value={config.fee_priority} onChange={handleChange}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div className="control-group">
            <label>Momentum Priority</label>
            <select name="momentum_priority" value={config.momentum_priority} onChange={handleChange}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div className="control-group">
            <label>Portfolio Size (N): {config.n}</label>
            <input 
              type="range" 
              name="n" 
              min="3" max="20" 
              value={config.n} 
              onChange={handleChange} 
            />
          </div>

          <div className="control-group" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input 
              type="checkbox" 
              name="news_enabled" 
              id="news_enabled"
              checked={config.news_enabled} 
              onChange={handleChange} 
              style={{ width: 'auto', margin: 0 }}
            />
            <label htmlFor="news_enabled" style={{ margin: 0, cursor: 'pointer' }}>Enable News Pass</label>
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Generating...' : 'Generate Portfolio'}
          </button>
        </form>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {error && (
          <div className="glass-panel" style={{ borderLeft: '4px solid var(--danger)' }}>
            <h3 style={{ color: 'var(--danger)', margin: 0 }}>Error</h3>
            <p style={{ margin: '8px 0 0 0' }}>{error}</p>
          </div>
        )}

        {data && (
          <>
            {/* Summary Cards */}
            <div className="summary-cards">
              <div className="glass-panel stat-card">
                <Activity size={24} color="var(--accent-primary)" style={{ margin: '0 auto' }} />
                <div className="stat-value">{data.header.candidate_kept} / {data.header.candidate_total}</div>
                <div className="stat-label">Funds Evaluated</div>
              </div>
              <div className="glass-panel stat-card">
                <ShieldAlert size={24} color="var(--warning)" style={{ margin: '0 auto' }} />
                <div className="stat-value">{data.header.risk_level.toUpperCase()}</div>
                <div className="stat-label">Target Risk</div>
              </div>
              <div className="glass-panel stat-card">
                <Newspaper size={24} color={data.news_meta.enabled ? "var(--danger)" : "var(--text-secondary)"} style={{ margin: '0 auto' }} />
                <div className="stat-value">{data.news_meta.enabled ? data.news_meta.total_hits : 'OFF'}</div>
                <div className="stat-label">News Penalties</div>
              </div>
            </div>

            {/* Charts Row */}
            <div className="charts-row">
              <div className="glass-panel">
                <h3 style={{ marginBottom: '24px' }}>Allocation by Strategy</h3>
                <div style={{ height: '300px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={strategyData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                        stroke="none"
                      >
                        {strategyData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip 
                        contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', border: '1px solid var(--panel-border)', borderRadius: '8px' }}
                        itemStyle={{ color: '#fff' }}
                        formatter={(value) => [`${value}%`, 'Allocation']}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Data Grid */}
            <div className="glass-panel">
              <h3 style={{ marginBottom: '24px' }}>Selected Portfolio</h3>
              {data.header.warning && (
                <div style={{ background: 'rgba(255, 184, 108, 0.1)', color: 'var(--warning)', padding: '12px', borderRadius: '8px', marginBottom: '16px' }}>
                  <AlertTriangle size={16} style={{ verticalAlign: 'middle', marginRight: '8px' }} />
                  {data.header.warning}
                </div>
              )}
              <div className="data-table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Fund</th>
                      <th>Strategy</th>
                      <th>Sector</th>
                      <th>Weight</th>
                      <th>Score</th>
                      <th>Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.weighted.map((fund) => (
                      <tr key={fund.fon_kodu}>
                        <td>
                          <strong>{fund.fon_kodu}</strong> - {fund.fon_adi}
                          {data.hits_for_render && data.hits_for_render[fund.fon_kodu] && (
                            <span title="Penalized due to negative news" style={{ marginLeft: '8px', cursor: 'help' }}>📰</span>
                          )}
                        </td>
                        <td><span className="badge strategy">{fund.strategy}</span></td>
                        <td>
                          {fund.sector !== 'diversified' ? (
                            <span className="badge sector">{fund.sector}</span>
                          ) : (
                            <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>DIVERSIFIED</span>
                          )}
                        </td>
                        <td><strong style={{ color: 'var(--accent-primary)' }}>{fund.display_weight_pct}%</strong></td>
                        <td>{fund.score?.toFixed(4)}</td>
                        <td>{fund.risk}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* News Penalties */}
            {data.news_meta && data.news_meta.enabled && (data.news_meta.total_hits > 0) && (
              <div className="glass-panel">
                <h3 style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Newspaper size={20} /> News Pass Results
                </h3>
                
                {/* Surviving Hits (Portföyde Kaldı) */}
                {Object.keys(data.hits_for_render || {}).length > 0 && (
                  <div style={{ marginBottom: '24px' }}>
                    <h4 style={{ color: 'var(--warning)', marginBottom: '12px' }}>Surviving Hits (Portföyde Kaldı)</h4>
                    <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                      These funds were penalized but still scored high enough to remain in the portfolio.
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {Object.entries(data.hits_for_render).map(([code, hits]) => (
                        <div key={`survivor-${code}`} style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '16px', borderRadius: '8px' }}>
                          <strong style={{ display: 'block', marginBottom: '8px', color: 'var(--text-primary)' }}>{code}</strong>
                          <ul style={{ margin: 0, paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {hits.map((hit, idx) => (
                              <li key={idx} style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                                <a href={hit.url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent-primary)', textDecoration: 'none' }}>
                                  {hit.title}
                                </a>
                                <span style={{ marginLeft: '8px', fontSize: '0.8rem', opacity: 0.7 }}>({hit.source})</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Dropped Hits (Portföyden Düşen) */}
                {data.news_meta.displaced && data.news_meta.displaced.length > 0 && (
                  <div>
                    <h4 style={{ color: 'var(--danger)', marginBottom: '12px' }}>Dropped Hits (Portföyden Düşen)</h4>
                    <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                      These funds would have been picked, but were pushed out due to the news penalty.
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {data.news_meta.displaced.map((item) => (
                        <div key={`dropped-${item.fon_kodu}`} style={{ background: 'rgba(255, 85, 85, 0.05)', border: '1px solid rgba(255, 85, 85, 0.2)', padding: '16px', borderRadius: '8px' }}>
                          <div style={{ marginBottom: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <strong style={{ color: 'var(--text-primary)' }}>{item.fon_kodu} - {item.fon_adi}</strong>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                              Score: <span style={{ textDecoration: 'line-through', opacity: 0.7 }}>{item.score_pre.toFixed(4)}</span> &rarr; <span style={{ color: 'var(--danger)' }}>{item.score_post.toFixed(4)}</span>
                            </div>
                          </div>
                          <ul style={{ margin: 0, paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {item.hits.map((hit, idx) => (
                              <li key={idx} style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                                <a href={hit.url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent-primary)', textDecoration: 'none' }}>
                                  {hit.title}
                                </a>
                                <span style={{ marginLeft: '8px', fontSize: '0.8rem', opacity: 0.7 }}>({hit.source})</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
