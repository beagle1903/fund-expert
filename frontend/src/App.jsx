import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { generatePortfolio } from './api/fundexpert.js';
import ControlPanel from './components/ControlPanel.jsx';
import ErrorPanel from './components/ErrorPanel.jsx';
import NewsResults from './components/NewsResults.jsx';
import PortfolioTable from './components/PortfolioTable.jsx';
import SummaryCards from './components/SummaryCards.jsx';
import { DEFAULT_CONFIG } from './config.js';

const AllocationChart = lazy(() => import('./components/AllocationChart.jsx'));

export default function App() {
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const activeRequest = useRef(null);

  const requestPortfolio = useCallback(async (requestConfig) => {
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    setLoading(true);
    setError(null);

    try {
      const result = await generatePortfolio(requestConfig, {
        signal: controller.signal,
      });
      if (activeRequest.current === controller) {
        setData(result);
      }
    } catch (requestError) {
      if (requestError.name !== 'AbortError' && activeRequest.current === controller) {
        setError(requestError.message);
      }
    } finally {
      if (activeRequest.current === controller) {
        activeRequest.current = null;
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    requestPortfolio(DEFAULT_CONFIG);
    return () => activeRequest.current?.abort();
  }, [requestPortfolio]);

  const handleGenerate = (event) => {
    event.preventDefault();
    requestPortfolio(config);
  };

  const handleChange = (event) => {
    const { checked, name, type, value } = event.target;
    const nextValue =
      type === 'checkbox' ? checked : type === 'range' ? Number(value) : value;
    setConfig((previous) => ({ ...previous, [name]: nextValue }));
  };

  return (
    <div className="dashboard-container">
      <ControlPanel
        config={config}
        loading={loading}
        onChange={handleChange}
        onSubmit={handleGenerate}
      />

      <main className="main-content">
        {error && <ErrorPanel message={error} />}

        {data && (
          <>
            <SummaryCards
              header={data.header}
              newsMeta={data.news_meta}
              snapshot={data.data_snapshot}
            />

            <div className="charts-row">
              <Suspense
                fallback={
                  <div className="glass-panel chart-loading" role="status">
                    Loading allocation chart…
                  </div>
                }
              >
                <AllocationChart weighted={data.weighted} />
              </Suspense>
            </div>

            <PortfolioTable
              header={data.header}
              hitsForRender={data.hits_for_render}
              weighted={data.weighted}
            />

            <NewsResults
              hitsForRender={data.hits_for_render}
              newsMeta={data.news_meta}
            />
          </>
        )}
      </main>
    </div>
  );
}
