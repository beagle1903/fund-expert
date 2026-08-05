export const DIVERSIFICATION_OPTIONS = [
  { value: 'strict', label: 'Strict' },
  { value: 'balanced', label: 'Balanced' },
  { value: 'relaxed', label: 'Relaxed' },
];

export const UNIVERSE_OPTIONS = [
  { value: 'tefas', label: 'TEFAS' },
  { value: 'befas', label: 'BEFAS' },
];

export const HORIZON_OPTIONS = [
  { value: 'short', label: 'Short' },
  { value: 'medium', label: 'Medium' },
  { value: 'long', label: 'Long' },
];

export const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
];

const DIVERSIFICATION_CAPS = {
  strict: [2, 2, 2],
  balanced: [2, 3, 4],
  relaxed: [3, 4, 5],
};

export function getDiversificationCap(n, mode) {
  const band = n <= 11 ? 0 : n <= 15 ? 1 : 2;
  return DIVERSIFICATION_CAPS[mode][band];
}

export const DEFAULT_CONFIG = {
  universe: 'tefas',
  founder: null,
  risk_level: 'medium',
  horizon: 'medium',
  volume_priority: 'medium',
  fee_priority: 'medium',
  momentum_priority: 'medium',
  n: 8,
  diversification_mode: 'balanced',
  news_enabled: false,
  refresh_data: true,
};
