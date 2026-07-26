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
    candidate_kept: 3,
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

function jsonResponse(body, { ok = true, status = 200 } = {}) {
  return Promise.resolve({
    ok,
    status,
    json: () => Promise.resolve(body),
  });
}

describe('App', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn(() => jsonResponse(responseBody));
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
  });

  it('submits portfolio size as a number', async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText('AAA');

    fireEvent.change(screen.getByLabelText(/Portfolio Size/), {
      target: { value: '12' },
    });
    await user.click(screen.getByRole('button', { name: 'Generate Portfolio' }));

    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    const payload = JSON.parse(fetch.mock.calls[1][1].body);
    expect(payload.n).toBe(12);
    expect(typeof payload.n).toBe('number');
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

    expect(screen.getByRole('button', { name: 'Generating…' })).toBeDisabled();
  });

  it('aborts the active request when unmounted', () => {
    globalThis.fetch = vi.fn(() => new Promise(() => {}));
    const { unmount } = render(<App />);
    const signal = fetch.mock.calls[0][1].signal;

    unmount();

    expect(signal.aborted).toBe(true);
  });
});
