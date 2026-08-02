import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./components/AllocationChart.jsx', () => ({
  default: () => <div>Allocation chart</div>,
}));

import App from './App.jsx';

const responseBody = {
  weighted: [
    {
      fon_kodu: 'AAA',
      fon_adi: 'ALPHA FON',
      strategy: 'mixed',
      sector: 'diversified',
      display_weight_pct: 100,
      score: 0.7123,
      risk: 4,
    },
  ],
  header: {
    timestamp: '2026-07-26T12:00:00',
    universe: 'tefas',
    candidate_total: 3,
    candidate_after_founder: 3,
    candidate_kept: 3,
    founder: null,
    horizon: 'medium',
    risk_level: 'medium',
    volume_priority: 'medium',
    fee_priority: 'medium',
    momentum_priority: 'medium',
    n: 8,
    warning: null,
    excluded_horizon: 0,
  },
  hits_for_render: {},
  news_meta: {
    enabled: false,
    key_present: null,
    top_k: null,
    total_hits: 0,
    displaced: [],
  },
  data_snapshot: {
    universe: 'tefas',
    bundle_id: 'bundle-1',
    source: 'legacy',
    exported_at: '2026-05-02T11:02:13',
    imported_at: null,
    row_count: 3,
  },
};

const selectionRulesBody = {
  bucket_rules: [
    { keyword: 'HİSSE SENEDİ', category: 'equity' },
    { keyword: 'DEĞİŞKEN', category: 'mixed' },
  ],
  sector_rules: [{ keyword: 'TEKNOLOJİ', category: 'tech' }],
  exclusion_rules: ['OKS'],
};

function jsonResponse(body, { ok = true, status = 200 } = {}) {
  return Promise.resolve({
    ok,
    status,
    json: () => Promise.resolve(body),
  });
}

describe('App', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn((url, options = {}) => {
      if (url.startsWith('/api/founders')) {
        return jsonResponse({
          universe: 'tefas',
          founders: [
            { name: 'AK PORTFÖY YÖNETİMİ A.Ş.', fund_count: 2 },
          ],
        });
      }
      if (url === '/api/selection-rules') {
        return jsonResponse(
          options.method === 'PUT'
            ? JSON.parse(options.body)
            : selectionRulesBody,
        );
      }
      return jsonResponse(responseBody);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('generates and renders the initial portfolio with provenance', async () => {
    render(<App />);

    expect(await screen.findByText('AAA')).toBeInTheDocument();
    expect(screen.getByText('2026-05-02 11:02')).toBeInTheDocument();
    expect(screen.getByText('Data Exported · legacy')).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(
      '/api/generate',
      expect.objectContaining({ method: 'POST' }),
    );
    const firstGenerate = fetch.mock.calls.find(
      ([url]) => url === '/api/generate',
    );
    expect(JSON.parse(firstGenerate[1].body).refresh_data).toBe(true);
  });

  it('submits portfolio size as a number', async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText('AAA');

    fireEvent.change(screen.getByLabelText(/Portfolio Size/), {
      target: { value: '12' },
    });
    await user.click(screen.getByRole('button', { name: 'Generate Portfolio' }));

    const generateCalls = () =>
      fetch.mock.calls.filter(([url]) => url === '/api/generate');
    await waitFor(() => expect(generateCalls()).toHaveLength(2));
    const payload = JSON.parse(generateCalls()[1][1].body);
    expect(payload.n).toBe(12);
    expect(typeof payload.n).toBe('number');
  });

  it('defaults to balanced diversification and submits it', async () => {
    render(<App />);
    await screen.findByText('AAA');

    expect(screen.getByLabelText('Diversification')).toHaveValue('balanced');
    const firstGenerate = fetch.mock.calls.find(
      ([url]) => url === '/api/generate',
    );
    expect(
      JSON.parse(firstGenerate[1].body).diversification_mode,
    ).toBe('balanced');
  });

  it('shows and submits the relaxed cap for a 12-fund portfolio', async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText('AAA');

    fireEvent.change(screen.getByLabelText(/Portfolio Size/), {
      target: { value: '12' },
    });
    await user.selectOptions(
      screen.getByLabelText('Diversification'),
      'relaxed',
    );

    expect(
      screen.getByText('Maximum 4 funds per strategy or named sector.'),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Generate Portfolio' }));
    const generateCalls = () =>
      fetch.mock.calls.filter(([url]) => url === '/api/generate');
    await waitFor(() => expect(generateCalls()).toHaveLength(2));
    expect(
      JSON.parse(generateCalls()[1][1].body).diversification_mode,
    ).toBe('relaxed');
  });

  it('loads universe-specific founders and resets the selection on universe change', async () => {
    globalThis.fetch = vi.fn((url) => {
      if (url === '/api/founders?universe=tefas') {
        return jsonResponse({
          universe: 'tefas',
          founders: [
            { name: 'AK PORTFÖY YÖNETİMİ A.Ş.', fund_count: 2 },
          ],
        });
      }
      if (url === '/api/founders?universe=befas') {
        return jsonResponse({
          universe: 'befas',
          founders: [
            { name: 'AGESA HAYAT VE EMEKLİLİK A.Ş.', fund_count: 8 },
          ],
        });
      }
      return jsonResponse(responseBody);
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText('AAA');

    await user.selectOptions(
      screen.getByLabelText('Founder (Kurucu)'),
      'AK PORTFÖY YÖNETİMİ A.Ş.',
    );
    expect(screen.getByLabelText('Founder (Kurucu)')).toHaveValue(
      'AK PORTFÖY YÖNETİMİ A.Ş.',
    );

    await user.selectOptions(screen.getByLabelText('Universe'), 'befas');

    await waitFor(() =>
      expect(
        screen.getByRole('option', {
          name: 'AGESA HAYAT VE EMEKLİLİK A.Ş. (8)',
        }),
      ).toBeInTheDocument(),
    );
    expect(screen.getByLabelText('Founder (Kurucu)')).toHaveValue('');
  });

  it('shows safe API error details', async () => {
    globalThis.fetch = vi.fn(() =>
      jsonResponse(
        {
          detail: {
            code: 'DATA_UNAVAILABLE',
            message: 'Data for TEFAS is unavailable or invalid.',
          },
        },
        { ok: false, status: 503 },
      ),
    );

    render(<App />);

    expect(
      await screen.findByText('Data for TEFAS is unavailable or invalid.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('disables submission while a request is pending', () => {
    globalThis.fetch = vi.fn(() => new Promise(() => {}));

    render(<App />);

    expect(
      screen.getByRole('button', { name: 'Refreshing & Generating…' }),
    ).toBeDisabled();
  });

  it('can explicitly generate with the existing data bundle', async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText('AAA');

    await user.click(
      screen.getByLabelText('Refresh stale TEFAS data before generating'),
    );
    await user.click(screen.getByRole('button', { name: 'Generate Portfolio' }));

    const generateCalls = () =>
      fetch.mock.calls.filter(([url]) => url === '/api/generate');
    await waitFor(() => expect(generateCalls()).toHaveLength(2));
    expect(JSON.parse(generateCalls()[1][1].body).refresh_data).toBe(false);
  });

  it('aborts the active request when unmounted', () => {
    globalThis.fetch = vi.fn(() => new Promise(() => {}));
    const { unmount } = render(<App />);
    const signal = fetch.mock.calls[0][1].signal;

    unmount();

    expect(signal.aborted).toBe(true);
  });

  it('edits selection rules and rebuilds with the existing data bundle', async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText('AAA');

    await user.click(
      screen.getByRole('button', { name: 'Edit Selection Rules' }),
    );
    expect(
      await screen.findByRole('dialog', { name: 'Selection Rules' }),
    ).toBeInTheDocument();

    const keyword = screen.getByLabelText('bucket_rules keyword 1');
    await user.clear(keyword);
    await user.type(keyword, 'HİSSE');
    await user.click(screen.getByRole('button', { name: 'Move rule 2 up' }));
    await user.click(screen.getByRole('button', { name: 'Save & Rebuild' }));

    const putCalls = () =>
      fetch.mock.calls.filter(
        ([url, options]) =>
          url === '/api/selection-rules' && options?.method === 'PUT',
      );
    await waitFor(() => expect(putCalls()).toHaveLength(1));
    const saved = JSON.parse(putCalls()[0][1].body);
    expect(saved.bucket_rules).toEqual([
      { keyword: 'DEĞİŞKEN', category: 'mixed' },
      { keyword: 'HİSSE', category: 'equity' },
    ]);

    await waitFor(() =>
      expect(
        fetch.mock.calls.filter(([url]) => url === '/api/generate'),
      ).toHaveLength(2),
    );
    const rebuild = fetch.mock.calls.filter(
      ([url]) => url === '/api/generate',
    )[1];
    expect(JSON.parse(rebuild[1].body).refresh_data).toBe(false);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('blocks duplicate rule keywords before saving', async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText('AAA');
    await user.click(
      screen.getByRole('button', { name: 'Edit Selection Rules' }),
    );
    await screen.findByRole('dialog', { name: 'Selection Rules' });

    await user.click(screen.getByRole('button', { name: 'Add rule' }));
    await user.type(screen.getByLabelText('bucket_rules keyword 3'), 'değişken');
    await user.type(screen.getByLabelText('bucket_rules category 3'), 'mixed');
    await user.click(screen.getByRole('button', { name: 'Save & Rebuild' }));

    expect(
      screen.getByRole('alert'),
    ).toHaveTextContent('Keywords must be unique within each section.');
    expect(
      fetch.mock.calls.filter(
        ([url, options]) =>
          url === '/api/selection-rules' && options?.method === 'PUT',
      ),
    ).toHaveLength(0);
  });
});
