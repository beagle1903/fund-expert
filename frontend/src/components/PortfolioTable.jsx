import { AlertTriangle } from 'lucide-react';

export default function PortfolioTable({ header, hitsForRender, weighted }) {
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
            {weighted.map((fund) => (
              <tr key={fund.fon_kodu}>
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
                <td>{fund.score?.toFixed(4)}</td>
                <td>{fund.risk ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
