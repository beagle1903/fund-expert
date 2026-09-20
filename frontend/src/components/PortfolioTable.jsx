import { Fragment, useState } from 'react';
import { AlertTriangle } from 'lucide-react';

const SIGNALS = [
  { key: 'return_contrib', label: 'Return', signed: false },
  { key: 'volume_contrib', label: 'Size', signed: false },
  { key: 'fee_contrib', label: 'Fee', signed: false },
  { key: 'momentum_contrib', label: 'Momentum', signed: false },
  { key: 'risk_penalty', label: 'Risk penalty', signed: true },
  { key: 'news_penalty', label: 'News penalty', signed: true },
];

function formatSignal(value, signed) {
  const magnitude = Math.abs(value).toFixed(4);
  if (!signed) {
    return magnitude;
  }
  return value === 0 ? magnitude : `−${magnitude}`;
}

export default function PortfolioTable({ header, hitsForRender, weighted }) {
  const [openCode, setOpenCode] = useState(null);

  return (
    <div className="glass-panel">
      <h3 className="section-heading">Selected Portfolio</h3>
      {header.founder && (
        <p className="portfolio-filter">Founder: {header.founder}</p>
      )}
      {header.warning && (
        <div className="portfolio-warning">
          <AlertTriangle size={16} />
          {header.warning}
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
            {weighted.map((fund) => {
              const isOpen = openCode === fund.fon_kodu;
              return (
                <Fragment key={fund.fon_kodu}>
                  <tr>
                    <td>
                      <strong>{fund.fon_kodu}</strong> - {fund.fon_adi}
                      {hitsForRender?.[fund.fon_kodu] && (
                        <span
                          title="Penalized due to negative news"
                          className="news-marker"
                        >
                          📰
                        </span>
                      )}
                    </td>
                    <td>
                      <span className="badge strategy">{fund.strategy}</span>
                    </td>
                    <td>
                      {fund.sector !== 'diversified' ? (
                        <span className="badge sector">{fund.sector}</span>
                      ) : (
                        <span className="diversified-label">DIVERSIFIED</span>
                      )}
                    </td>
                    <td>
                      <strong className="weight-value">{fund.display_weight_pct}%</strong>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="score-breakdown-toggle"
                        aria-expanded={isOpen}
                        aria-label={`Show score breakdown for ${fund.fon_kodu}`}
                        onClick={() =>
                          setOpenCode(isOpen ? null : fund.fon_kodu)
                        }
                      >
                        {fund.score?.toFixed(4)}
                      </button>
                    </td>
                    <td>{fund.risk ?? '—'}</td>
                  </tr>
                  {isOpen && fund.breakdown && (
                    <tr className="score-breakdown-row">
                      <td colSpan={6}>
                        <dl className="score-breakdown">
                          {SIGNALS.map((signal) => (
                            <div key={signal.key}>
                              <dt>{signal.label}</dt>
                              <dd className={signal.signed ? 'penalty' : undefined}>
                                {formatSignal(
                                  fund.breakdown[signal.key],
                                  signal.signed,
                                )}
                              </dd>
                            </div>
                          ))}
                        </dl>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
