import { Newspaper } from 'lucide-react';

function HitList({ hits }) {
  return (
    <ul className="news-hit-list">
      {hits.map((hit) => (
        <li key={`${hit.url}-${hit.title}`}>
          <a href={hit.url} target="_blank" rel="noreferrer">
            {hit.title}
          </a>
          <span>({hit.source})</span>
        </li>
      ))}
    </ul>
  );
}

export default function NewsResults({ hitsForRender, newsMeta }) {
  if (!newsMeta?.enabled || newsMeta.total_hits <= 0) {
    return null;
  }

  return (
    <div className="glass-panel">
      <h3 className="news-heading">
        <Newspaper size={20} /> News Pass Results
      </h3>

      {Object.keys(hitsForRender || {}).length > 0 && (
        <section className="news-section">
          <h4 className="surviving-heading">Surviving Hits (Portföyde Kaldı)</h4>
          <p>
            These funds were penalized but still scored high enough to remain in
            the portfolio.
          </p>
          <div className="news-card-list">
            {Object.entries(hitsForRender).map(([code, hits]) => (
              <article className="news-card" key={code}>
                <strong>{code}</strong>
                <HitList hits={hits} />
              </article>
            ))}
          </div>
        </section>
      )}

      {newsMeta.displaced?.length > 0 && (
        <section>
          <h4 className="dropped-heading">Dropped Hits (Portföyden Düşen)</h4>
          <p>
            These funds would have been picked, but were pushed out due to the
            news penalty.
          </p>
          <div className="news-card-list">
            {newsMeta.displaced.map((item) => (
              <article className="news-card dropped-news-card" key={item.fon_kodu}>
                <div className="dropped-news-header">
                  <strong>
                    {item.fon_kodu} - {item.fon_adi}
                  </strong>
                  <span>
                    Score: <s>{item.score_pre.toFixed(4)}</s> →{' '}
                    <em>{item.score_post.toFixed(4)}</em>
                  </span>
                </div>
                <HitList hits={item.hits} />
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
