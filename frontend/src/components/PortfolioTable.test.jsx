import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import PortfolioTable from './PortfolioTable.jsx';

const weighted = [
  {
    fon_kodu: 'AAA',
    fon_adi: 'ALPHA FON',
    strategy: 'mixed',
    sector: 'diversified',
    display_weight_pct: 100,
    score: 0.55,
    risk: 4,
    breakdown: {
      return_contrib: 0.4,
      volume_contrib: 0.2,
      fee_contrib: 0.15,
      momentum_contrib: 0.1,
      risk_penalty: 0.1,
      news_penalty: 0.2,
    },
  },
];

const header = {
  founder: null,
  warning: null,
};

describe('PortfolioTable', () => {
  it('lets the user inspect per-signal score contributions', async () => {
    const user = userEvent.setup();
    render(
      <PortfolioTable header={header} hitsForRender={{}} weighted={weighted} />,
    );

    expect(screen.getByText('0.5500')).toBeInTheDocument();
    expect(screen.queryByText('Return')).not.toBeInTheDocument();

    await user.click(
      screen.getByRole('button', { name: /show score breakdown for AAA/i }),
    );

    expect(screen.getByText('Return')).toBeInTheDocument();
    expect(screen.getByText('0.4000')).toBeInTheDocument();
    expect(screen.getByText('Size')).toBeInTheDocument();
    expect(screen.getByText('Fee')).toBeInTheDocument();
    expect(screen.getByText('Momentum')).toBeInTheDocument();
    expect(screen.getByText('Risk penalty')).toBeInTheDocument();
    expect(screen.getByText('News penalty')).toBeInTheDocument();
    expect(screen.getByText('−0.2000')).toBeInTheDocument();
  });
});
