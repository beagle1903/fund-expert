import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import NewsResults from './NewsResults.jsx';

const hit = {
  title: 'Regulator announces a penalty',
  url: 'https://example.com/news',
  source: 'example.com',
};

describe('NewsResults', () => {
  it('renders surviving and displaced news hits', () => {
    render(
      <NewsResults
        hitsForRender={{ AAA: [hit] }}
        newsMeta={{
          enabled: true,
          total_hits: 2,
          displaced: [
            {
              fon_kodu: 'BBB',
              fon_adi: 'BETA FON',
              score_pre: 0.8,
              score_post: 0.6,
              hits: [{ ...hit, url: 'https://example.com/other' }],
            },
          ],
        }}
      />,
    );

    expect(screen.getByText('Surviving Hits (Portföyde Kaldı)')).toBeInTheDocument();
    expect(screen.getByText('Dropped Hits (Portföyden Düşen)')).toBeInTheDocument();
    expect(screen.getByText('BBB - BETA FON')).toBeInTheDocument();
    expect(screen.getAllByText('Regulator announces a penalty')).toHaveLength(2);
  });

  it('renders nothing when the news pass is disabled', () => {
    const { container } = render(
      <NewsResults
        hitsForRender={{}}
        newsMeta={{ enabled: false, total_hits: 0, displaced: [] }}
      />,
    );

    expect(container).toBeEmptyDOMElement();
  });
});
