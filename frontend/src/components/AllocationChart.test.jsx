import { describe, expect, it } from 'vitest';
import {
  allocationByStrategy,
  strategyAllocationLabel,
  strategyDisplayName,
} from '../utils/allocation.js';

describe('allocationByStrategy', () => {
  it('aggregates weights by strategy', () => {
    expect(
      allocationByStrategy([
        { strategy: 'equity', display_weight_pct: 30 },
        { strategy: 'equity', display_weight_pct: 20 },
        { strategy: 'debt', display_weight_pct: 50 },
      ]),
    ).toEqual([
      { name: 'equity', value: 50 },
      { name: 'debt', value: 50 },
    ]);
  });

  it('formats readable labels with percentages', () => {
    expect(strategyDisplayName('money_market')).toBe('Money market');
    expect(strategyDisplayName('other')).toBe('Unclassified');
    expect(strategyAllocationLabel({ name: 'fund_of_funds', value: 25 })).toBe(
      'Fund of funds · 25%',
    );
  });
});
