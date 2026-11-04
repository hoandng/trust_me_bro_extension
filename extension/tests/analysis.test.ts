import assert from 'node:assert/strict';
import { afterEach, beforeEach, test } from 'node:test';
import { handleAnalysisRequest } from '../src/features/analysis/background/handle-analysis';
import { mapAnalysisResponse } from '../src/features/analysis/background/map-response';
import {
  getTabState,
  setTabState,
  subscribeToTabStates,
} from '../src/features/analysis/state-store';
import { isAnalyzeRequest } from '../src/shared/messages';
import type { AnalyzeRequestMessage } from '../src/shared/messages';
import type { BackendAnalysisResponse } from '../src/features/analysis/types';

const originalFetch = globalThis.fetch;
const originalChrome = globalThis.chrome;
const values = new Map<string, unknown>();
const listeners = new Set<(changes: Record<string, chrome.storage.StorageChange>) => void>();
const request: AnalyzeRequestMessage = {
  type: 'ANALYZE_REQUEST',
  payload: {
    text: 'Nội dung cần được kiểm chứng.',
    platform: 'facebook',
    page_url: 'https://www.facebook.com/',
  },
};
const sender: chrome.runtime.MessageSender = { tab: { id: 7 } as chrome.tabs.Tab };
const backendResponse: BackendAnalysisResponse = {
  verdict: 'likely_true',
  confidence_score: 0.82,
  explanation: 'Có nguồn đối chứng.',
  sources: [{ title: 'Nguồn tin', url: 'https://example.com', publisher_name: 'Nhà xuất bản' }],
  service_status: { gemini: 'ok', tavily: 'ok', factcheck: 'empty' },
};

beforeEach(() => {
  values.clear();
  listeners.clear();
  globalThis.chrome = {
    storage: {
      local: {
        get: async (key: string) => ({ [key]: values.get(key) }),
        set: async (items: Record<string, unknown>) => {
          for (const [key, value] of Object.entries(items)) values.set(key, value);
        },
      },
      session: {
        get: async (key: string) => ({ [key]: values.get(key) }),
        set: async (items: Record<string, unknown>) => {
          for (const [key, newValue] of Object.entries(items)) {
            const oldValue = values.get(key);
            values.set(key, newValue);
            for (const listener of listeners) listener({ [key]: { oldValue, newValue } });
          }
        },
        onChanged: {
          addListener: (
            listener: (changes: Record<string, chrome.storage.StorageChange>) => void,
          ) => listeners.add(listener),
          removeListener: (
            listener: (changes: Record<string, chrome.storage.StorageChange>) => void,
          ) => listeners.delete(listener),
        },
      },
    },
    sidePanel: { open: async () => {}, setOptions: async () => {} },
    action: { setBadgeText: async () => {}, setBadgeBackgroundColor: async () => {} },
  } as unknown as typeof chrome;
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  globalThis.chrome = originalChrome;
});

test('chỉ nhận message có đúng hợp đồng phân tích', () => {
  assert.equal(isAnalyzeRequest(request), true);
  assert.equal(isAnalyzeRequest({ ...request, payload: { text: 123 } }), false);
  assert.equal(isAnalyzeRequest({ ...request, tabId: '7' }), false);
  assert.equal(isAnalyzeRequest({ type: 'UNKNOWN' }), false);
  assert.equal(isAnalyzeRequest(null), false);
});

test('chuyển response backend sang dữ liệu UI và giữ cảnh báo service', () => {
  const result = mapAnalysisResponse({ ...backendResponse, service_status: { gemini: 'error' } });
  assert.equal(result.verdict, 'Thật');
  assert.equal(result.confidence, 82);
  assert.equal(result.sources[0].publisher, 'Nhà xuất bản');
  assert.equal(result.service_status, 'error');
  assert.equal(
    mapAnalysisResponse({ ...backendResponse, verdict: 'unknown' }).verdict,
    'Không thể kiểm chứng',
  );
});

test('trạng thái và subscription tách biệt theo tab, có thể ngừng theo dõi', async () => {
  const observed: number[] = [];
  const unsubscribe = subscribeToTabStates((tabId) => observed.push(tabId));
  await setTabState(7, { status: 'loading', request: request.payload });
  await setTabState(8, { status: 'error', error: 'Lỗi tab khác' });
  assert.equal((await getTabState(7))?.status, 'loading');
  assert.equal((await getTabState(8))?.status, 'error');
  assert.deepEqual(observed, [7, 8]);
  unsubscribe();
  await setTabState(7, { status: 'idle' });
  assert.deepEqual(observed, [7, 8]);
});

test('yêu cầu đi qua loading → API → success, gửi đúng payload và header', async () => {
  let finishFetch!: (response: Response) => void;
  globalThis.fetch = async (url, options) => {
    assert.equal(url, 'http://127.0.0.1:8000/api/v1/analyze');
    assert.equal(options?.method, 'POST');
    assert.equal(new Headers(options?.headers).get('X-API-Key'), 'test-key');
    assert.deepEqual(JSON.parse(options?.body as string), request.payload);
    return new Promise<Response>((resolve) => {
      finishFetch = resolve;
    });
  };
  const pending = handleAnalysisRequest(request, sender);
  await new Promise<void>((resolve) => setImmediate(resolve));
  assert.equal((await getTabState(7))?.status, 'loading');
  finishFetch(Response.json(backendResponse));
  await pending;
  assert.equal((await getTabState(7))?.status, 'success');
  assert.equal((await getTabState(7))?.response?.confidence, 82);
});

test('lỗi HTTP chuyển sang trạng thái error và giữ request để retry đúng tab', async () => {
  globalThis.fetch = async () => new Response(null, { status: 429 });
  await handleAnalysisRequest({ ...request, tabId: 8 }, sender);
  const state = await getTabState(8);
  assert.equal(state?.status, 'error');
  assert.equal(state?.error, 'Quá nhiều yêu cầu (429)');
  assert.deepEqual(state?.request, request.payload);
  assert.equal(await getTabState(7), undefined);
});

test('lỗi kết nối được chuyển thành thông báo dễ hiểu', async () => {
  globalThis.fetch = async () => {
    throw new TypeError('fetch failed');
  };
  await handleAnalysisRequest(request, sender);
  assert.equal((await getTabState(7))?.status, 'error');
  assert.match((await getTabState(7))?.error || '', /Lỗi kết nối/);
});

test('model đã lưu được dùng cho request tiếp theo và ghi vào state', async () => {
  values.set('preferredGeminiModel', 'gemini-test');
  globalThis.fetch = async (_url, options) => {
    assert.equal(JSON.parse(options?.body as string).model_id, 'gemini-test');
    values.set('preferredGeminiModel', 'changed-during-request');
    return Response.json(backendResponse);
  };
  await handleAnalysisRequest(request, sender);
  assert.equal((await getTabState(7))?.request?.model_id, 'gemini-test');
  assert.equal(values.get('preferredGeminiModel'), 'changed-during-request');
});

test('giữ metadata model và thông báo hết quota từ backend', async () => {
  const usage = { requested_model: 'a', extraction_model: 'b', assessment_model: 'b',
    fallbacks: [{ stage: 'extraction', model: 'a', reason: 'quota' }] };
  assert.deepEqual(mapAnalysisResponse({ ...backendResponse, model_usage: usage }).model_usage, usage);
  globalThis.fetch = async () => Response.json({ detail: 'Tất cả model chạm hạn mức' }, { status: 503 });
  await handleAnalysisRequest(request, sender);
  assert.equal((await getTabState(7))?.error, 'Tất cả model chạm hạn mức');
});
