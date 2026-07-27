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

export function strategyDisplayName(strategy) {
  if (!strategy || strategy === 'other') {
    return 'Unclassified';
  }

  const words = strategy.replaceAll('_', ' ');
  return `${words.charAt(0).toUpperCase()}${words.slice(1)}`;
}

export function strategyAllocationLabel({ name, value }) {
  return `${strategyDisplayName(name)} · ${value}%`;
}
