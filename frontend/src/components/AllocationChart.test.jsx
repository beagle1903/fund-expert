import { describe, expect, it } from 'vitest';
import { allocationByStrategy } from '../utils/allocation.js';

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
});
