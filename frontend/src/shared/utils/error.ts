/**
 * ServicePulse - Safe API Error Formatting Helper
 * Prevents React child rendering crashes by converting any error or FastAPI 422
 * validation detail (string, array of objects, or dictionary) into a safe, clean string.
 */
export function getApiErrorMessage(err: unknown, fallback: string): string {
  if (!err || typeof err !== 'object') {
    return fallback;
  }

  const axiosErr = err as {
    response?: {
      data?: {
        detail?: string | Array<{ loc?: string[]; msg?: string; type?: string }> | Record<string, unknown>;
        message?: string;
      };
    };
    message?: string;
  };

  const detail = axiosErr.response?.data?.detail;

  if (typeof detail === 'string' && detail.trim().length > 0) {
    return detail.trim();
  }

  if (Array.isArray(detail) && detail.length > 0) {
    // Pydantic validation errors: array of {loc, msg, type}
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (item && typeof item === 'object' && item.msg) {
          const field = Array.isArray(item.loc) && item.loc.length > 1 ? `${item.loc[item.loc.length - 1]}: ` : '';
          return `${field}${item.msg}`;
        }
        return '';
      })
      .filter((m) => m.length > 0);

    if (messages.length > 0) {
      return messages.join('; ');
    }
  }

  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const values = Object.values(detail)
      .map((v) => (typeof v === 'string' ? v : JSON.stringify(v)))
      .filter((v) => v.length > 0);
    if (values.length > 0) {
      return values.join('; ');
    }
  }

  if (axiosErr.response?.data?.message) {
    return axiosErr.response.data.message;
  }

  if (axiosErr.message && typeof axiosErr.message === 'string') {
    return axiosErr.message;
  }

  return fallback;
}
