export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function validationMessage(detail) {
  if (!Array.isArray(detail)) {
    return null;
  }
  const messages = detail
    .map((item) => item?.msg)
    .filter((message) => typeof message === 'string' && message.length > 0);
  return messages.length > 0 ? messages.join(' ') : null;
}

export function extractApiError(payload, response) {
  const detail = payload?.detail;
  if (typeof detail === 'string') {
    return detail;
  }
  if (detail && typeof detail.message === 'string') {
    return detail.message;
  }
  return validationMessage(detail) || `Request failed with status ${response.status}.`;
}

export async function generatePortfolio(config, { signal } = {}) {
  const response = await fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
    signal,
  });

  let payload;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new ApiError(extractApiError(payload, response), response.status);
  }
  return payload;
}
