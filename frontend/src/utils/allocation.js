export function allocationByStrategy(weighted) {
  const allocations = new Map();
  weighted.forEach((fund) => {
    const strategy = fund.strategy || 'Other';
    allocations.set(
      strategy,
      (allocations.get(strategy) || 0) + fund.display_weight_pct,
    );
  });
  return Array.from(allocations, ([name, value]) => ({ name, value }));
}
