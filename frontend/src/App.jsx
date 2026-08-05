import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { generatePortfolio, getFounders } from './api/fundexpert.js';
import BuildProfileSettings from './components/BuildProfileSettings.jsx';
import ControlPanel from './components/ControlPanel.jsx';
import ErrorPanel from './components/ErrorPanel.jsx';
import NewsResults from './components/NewsResults.jsx';
import PortfolioTable from './components/PortfolioTable.jsx';
import PortfolioSettings from './components/PortfolioSettings.jsx';
import RuleEditor from './components/RuleEditor.jsx';
import SummaryCards from './components/SummaryCards.jsx';
import { DEFAULT_CONFIG } from './config.js';

const AllocationChart = lazy(() => import('./components/AllocationChart.jsx'));

export default function App() {
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [data, setData] = useState(null);
  const [founders, setFounders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [buildProfileOpen, setBuildProfileOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [rulesOpen, setRulesOpen] = useState(false);
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

  useEffect(() => {
    const controller = new AbortController();
    setFounders([]);
    getFounders(config.universe, { signal: controller.signal })
      .then(setFounders)
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') {
          setFounders([]);
        }
      });
    return () => controller.abort();
  }, [config.universe]);

  const handleGenerate = (event) => {
    event.preventDefault();
    requestPortfolio(config);
  };

  const handleRulesSaved = () => {
    setRulesOpen(false);
    requestPortfolio({ ...config, refresh_data: false });
  };

  const handleSettingsApplied = (nextConfig) => {
    setConfig(nextConfig);
    setSettingsOpen(false);
  };

  return (
    <div className="dashboard-container">
      <ControlPanel
        config={config}
        loading={loading}
        onEditBuildProfile={() => setBuildProfileOpen(true)}
        onEditRules={() => setRulesOpen(true)}
        onEditSettings={() => setSettingsOpen(true)}
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

            <PortfolioTable
              header={data.header}
              hitsForRender={data.hits_for_render}
              weighted={data.weighted}
            />

            <NewsResults
              hitsForRender={data.hits_for_render}
              newsMeta={data.news_meta}
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
          </>
        )}
      </main>

      {buildProfileOpen && (
        <BuildProfileSettings onClose={() => setBuildProfileOpen(false)} />
      )}

      {settingsOpen && (
        <PortfolioSettings
          config={config}
          founders={founders}
          onClose={() => setSettingsOpen(false)}
          onApply={handleSettingsApplied}
        />
      )}

      {rulesOpen && (
        <RuleEditor
          onClose={() => setRulesOpen(false)}
          onSaved={handleRulesSaved}
        />
      )}
    </div>
  );
}
