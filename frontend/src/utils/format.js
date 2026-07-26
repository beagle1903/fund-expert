export function formatExportedAt(value) {
  return value ? value.replace('T', ' ').slice(0, 16) : 'UNKNOWN';
}
