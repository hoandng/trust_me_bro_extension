const backendUrl = (import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const apiKey = import.meta.env.VITE_EXTENSION_API_KEY || '';
const requestTimeoutMs = 60_000;

export async function postToBackend<TResponse>(path: string, payload: unknown): Promise<TResponse> {
  return requestBackend<TResponse>(path, 'POST', payload);
}

export async function getFromBackend<TResponse>(path: string): Promise<TResponse> {
  return requestBackend<TResponse>(path, 'GET');
}

async function requestBackend<TResponse>(path: string, method: string, payload?: unknown): Promise<TResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), requestTimeoutMs);

  try {
    const response = await fetch(`${backendUrl}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    if (!response.ok) {
      if (response.status === 401) throw new Error('Lỗi xác thực (401)');
      if (response.status === 422) throw new Error('Dữ liệu không hợp lệ (422)');
      if (response.status === 429) throw new Error('Quá nhiều yêu cầu (429)');
      if (response.status === 503) {
        const error = await response.json().catch(() => null);
        throw new Error(error?.detail || 'Dịch vụ AI tạm thời không khả dụng.');
      }
      if (response.status >= 500) throw new Error('Lỗi máy chủ hệ thống (5xx)');
      throw new Error(`Lỗi mạng (${response.status})`);
    }

    return (await response.json()) as TResponse;
  } catch (error) {
    if (error instanceof Error && (error.name === 'AbortError' || error instanceof TypeError)) {
      throw new Error('Lỗi kết nối hoặc yêu cầu quá thời gian chờ (60s)', { cause: error });
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}
