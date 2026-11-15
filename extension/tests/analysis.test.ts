import assert from 'node:assert/strict';
import { afterEach, beforeEach, test } from 'node:test';
import {
  forgetAnalysisTab, getLiveAnalysisState, handleAnalysisRequest, retryAnalysisForTab,
} from '../src/features/analysis/background/handle-analysis';
import { mapAnalysisResponse } from '../src/features/analysis/background/map-response';
import { buildShareSummary } from '../src/features/analysis/share-summary';
import {
  getTabState,
  setTabState,
  subscribeToTabStates,
} from '../src/features/analysis/state-store';
import { SIDEPANEL_PATH } from '../src/shared/config';
import { isAnalysisTabMessage, isAnalyzeRequest, isSubmitFeedbackMessage } from '../src/shared/messages';
import type { AnalyzeRequestMessage, SubmitFeedbackMessage } from '../src/shared/messages';
import type { BackendAnalysisResponse, FeedbackReply } from '../src/features/analysis/types';

const originalFetch = globalThis.fetch;
const originalChrome = globalThis.chrome;
const values = new Map<string, unknown>();
const listeners = new Set<(changes: Record<string, chrome.storage.StorageChange>) => void>();
type MessageListener = Parameters<typeof chrome.runtime.onMessage.addListener>[0];
let messageListener: MessageListener | undefined;
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
  request_id: '88a7b1c8-fb0b-44a8-9f07-02008a8ad22f',
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
        remove: async (key: string) => {
          const oldValue = values.get(key);
          values.delete(key);
          for (const listener of listeners) listener({ [key]: { oldValue } });
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
    sidePanel: { open: async () => {}, setOptions: async () => {}, setPanelBehavior: async () => {} },
    action: { setBadgeText: async () => {}, setBadgeBackgroundColor: async () => {} },
    tabs: { onRemoved: { addListener: () => {} }, onUpdated: { addListener: () => {} } },
    runtime: {
      getURL: (path: string) => `chrome-extension://mock/${path}`,
      onMessage: { addListener: (listener: MessageListener) => { messageListener = listener; } },
    },
  } as unknown as typeof chrome;
});

afterEach(async () => {
  await Promise.all([forgetAnalysisTab(7), forgetAnalysisTab(8)]);
  globalThis.fetch = originalFetch;
  globalThis.chrome = originalChrome;
});

test('chỉ nhận message có đúng hợp đồng phân tích', () => {
  assert.equal(isAnalyzeRequest(request), true);
  assert.equal(isAnalyzeRequest({ ...request, payload: { text: 123 } }), false);
  assert.equal(isAnalyzeRequest({ ...request, tabId: '7' }), false);
  assert.equal(isAnalyzeRequest({ type: 'UNKNOWN' }), false);
  assert.equal(isAnalyzeRequest(null), false);
  assert.equal(isAnalysisTabMessage({ type: 'GET_ANALYSIS_STATE', tabId: 7 }), true);
  assert.equal(isAnalysisTabMessage({ type: 'RETRY_ANALYSIS', tabId: -1 }), false);
});

test('chuyển response backend sang dữ liệu UI và giữ cảnh báo service', () => {
  const result = mapAnalysisResponse({ ...backendResponse, service_status: { gemini: 'error' } });
  assert.equal(result.verdict, 'Thật');
  assert.equal(result.confidence, 82);
  assert.equal(result.sources[0].publisher, 'Nhà xuất bản');
  assert.equal(result.service_status, 'error');
  assert.equal(result.request_id, backendResponse.request_id);
  assert.equal(
    mapAnalysisResponse({ ...backendResponse, verdict: 'unknown' }).verdict,
    'Không thể kiểm chứng',
  );
});

test('mapping kết luận đời thường và fallback cho verdict lạ', () => {
  const expected = {
    likely_true: 'Có vẻ đúng sự thật',
    likely_false: 'Có vẻ sai sự thật',
    mixed: 'Cần xem thêm ngữ cảnh',
    unverified: 'Chưa đủ bằng chứng, đừng vội chia sẻ',
    toString: 'Chưa đủ bằng chứng, đừng vội chia sẻ',
  };
  for (const [verdict, conclusion] of Object.entries(expected)) {
    assert.equal(mapAnalysisResponse({ ...backendResponse, verdict }).conclusion, conclusion);
  }
});

test('mapping tên nguồn, ngày xuất bản và lập trường', () => {
  const { sources } = mapAnalysisResponse({
    ...backendResponse,
    sources: [
      {
        title: 'Bài báo', url: 'https://www.reuters.com/article', publisher: 'Reuters',
        publisher_name: 'reuters.com', published_date: '2026-11-10', stance: 'supports',
      },
      {
        title: 'Bài kiểm chứng', url: 'https://news.example.com/check',
        published_date: 'Tue, 10 Nov 2026 20:00:00 GMT', stance: 'refutes',
      },
      {
        title: '<img src=x>', url: 'javascript:void(0)', publisher_name: null,
        published_date: '2026-02-31', stance: 'unsupported',
      },
    ],
  });
  assert.deepEqual(sources.map((source) => [source.publisher, source.publishedDate, source.stance]), [
    ['Reuters', '10/11/2026', 'supports'],
    ['news.example.com', '11/11/2026', 'refutes'],
    ['Nguồn bên ngoài', undefined, undefined],
  ]);
  assert.equal(sources[2].url, '');
  assert.equal(sources[2].title, '<img src=x>');
});

test('bản chia sẻ lấy tối đa hai lý do và hai URL nguồn khác nhau', () => {
  const result = mapAnalysisResponse({
    ...backendResponse,
    verdict: 'likely_false',
    explanation: 'Nguồn thứ nhất bác bỏ claim. Số liệu không khớp. Lý do thứ ba.',
    sources: [
      { title: 'Bài gốc', url: request.payload.page_url },
      { title: 'Link lỗi', url: 'javascript:void(0)' },
      { title: 'Một', url: 'https://example.com/a#intro' },
      { title: 'Bản trùng', url: 'https://example.com/a#result' },
      { title: 'Hai', url: 'https://example.com/b' },
      { title: 'Ba', url: 'https://example.com/c' },
    ],
  });
  assert.deepEqual(buildShareSummary(result, request.payload).split('\n'), [
    'Kết luận: Có vẻ sai sự thật',
    '',
    '- Nguồn thứ nhất bác bỏ claim.',
    '- Số liệu không khớp.',
    '',
    'Nguồn tham khảo:',
    'https://example.com/a',
    'https://example.com/b',
    '',
    'Kết quả do AI tổng hợp, chỉ mang tính tham khảo.',
  ]);
  const echoed = buildShareSummary({ ...result, explanation: request.payload.text, sources: [] }, request.payload);
  assert.ok(!echoed.includes(request.payload.text));
  assert.ok(!echoed.includes('Nguồn tham khảo'));
});

test('background chỉ gửi feedback từ side panel cho UUID hiện tại và nhận 204', async () => {
  await import('../src/entrypoints/background');
  assert.ok(messageListener);
  const listener = messageListener;
  const panel = { url: chrome.runtime.getURL(SIDEPANEL_PATH) };
  globalThis.fetch = async () => Response.json(backendResponse);
  await handleAnalysisRequest(request, sender);

  const message: SubmitFeedbackMessage = {
    type: 'SUBMIT_ANALYSIS_FEEDBACK', tabId: 7, request_id: backendResponse.request_id!, helpful: true,
  };
  assert.ok(isSubmitFeedbackMessage(message));
  assert.equal(isSubmitFeedbackMessage({ ...message, helpful: 'true' }), false);
  assert.equal(isSubmitFeedbackMessage({ ...message, request_id: 'not-a-uuid' }), false);
  assert.equal(isSubmitFeedbackMessage({ ...message, tabId: -1 }), false);

  let posts = 0;
  let replyStatus = 204;
  const bodies: unknown[] = [];
  globalThis.fetch = async (url, options) => {
    posts += 1;
    assert.equal(url, 'http://127.0.0.1:8000/api/v1/feedback');
    assert.equal(options?.method, 'POST');
    assert.equal(new Headers(options?.headers).get('X-API-Key'), 'test-key');
    bodies.push(JSON.parse(options?.body as string));
    return new Response(null, { status: replyStatus });
  };
  function send(value: SubmitFeedbackMessage): Promise<FeedbackReply> {
    return new Promise((resolve) => {
      assert.equal(listener(value, panel, resolve), true);
    });
  }

  assert.equal(listener(message, { ...sender, url: request.payload.page_url }, () => {
    assert.fail('Message from the page should be ignored');
  }), undefined);
  assert.equal((await send({ ...message, request_id: '96822b5b-4e4a-4218-9e78-8d793f9770a6' })).ok, false);
  assert.equal(posts, 0);
  assert.deepEqual(await send(message), { ok: true });
  assert.deepEqual(await send(message), { ok: true });
  assert.equal(posts, 1);
  assert.equal(getLiveAnalysisState(7)?.feedback, true);
  assert.deepEqual(await getTabState(7), { status: 'success', request_id: message.request_id });

  replyStatus = 429;
  const failed = await send({ ...message, helpful: false });
  assert.deepEqual(failed, { ok: false, error: 'Chưa gửi được phản hồi. Hãy thử lại sau.' });
  assert.equal(getLiveAnalysisState(7)?.feedback, true);
  replyStatus = 204;
  assert.deepEqual(await send({ ...message, helpful: false }), { ok: true });
  assert.equal(getLiveAnalysisState(7)?.feedback, false);
  assert.deepEqual(bodies, [true, false, false].map((helpful) => ({ request_id: message.request_id, helpful })));
});

test('trạng thái và subscription tách biệt theo tab, có thể ngừng theo dõi', async () => {
  const observed: number[] = [];
  const unsubscribe = subscribeToTabStates((tabId) => observed.push(tabId));
  await setTabState(7, { status: 'loading' });
  await setTabState(8, { status: 'error' });
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
  assert.deepEqual(await getTabState(7), { status: 'loading' });
  finishFetch(Response.json({
    ...backendResponse,
    explanation: request.payload.text,
    sources: [{ title: request.payload.text, url: request.payload.page_url }],
  }));
  await pending;
  assert.deepEqual(await getTabState(7), {
    status: 'success', request_id: backendResponse.request_id,
  });
  assert.equal(getLiveAnalysisState(7)?.response?.confidence, 82);
  assert.equal(getLiveAnalysisState(7)?.response?.explanation, request.payload.text);
  assert.doesNotMatch(JSON.stringify([...values]), /Nội dung cần|facebook\.com/);
});

test('lỗi HTTP chuyển sang trạng thái error và giữ request để retry đúng tab', async () => {
  globalThis.fetch = async () => new Response(null, { status: 429 });
  await handleAnalysisRequest({ ...request, tabId: 8 }, sender);
  assert.deepEqual(await getTabState(8), { status: 'error' });
  const state = getLiveAnalysisState(8);
  assert.equal(state?.status, 'error');
  assert.equal(state?.error, 'Quá nhiều yêu cầu (429)');
  assert.deepEqual(state?.request, request.payload);
  assert.equal(await getTabState(7), undefined);

  let attempts = 0;
  globalThis.fetch = async (_url, options) => {
    attempts += 1;
    assert.deepEqual(JSON.parse(options?.body as string), request.payload);
    return Response.json(backendResponse);
  };
  await retryAnalysisForTab(8);
  assert.equal(getLiveAnalysisState(8)?.status, 'success');
  await forgetAnalysisTab(8);
  await retryAnalysisForTab(8);
  assert.equal(attempts, 1);
  assert.equal(getLiveAnalysisState(8), undefined);
});

test('lỗi kết nối được chuyển thành thông báo dễ hiểu', async () => {
  globalThis.fetch = async () => {
    throw new TypeError('fetch failed');
  };
  await handleAnalysisRequest(request, sender);
  assert.equal((await getTabState(7))?.status, 'error');
  assert.match(getLiveAnalysisState(7)?.error || '', /Lỗi kết nối/);
});

test('model đã lưu được dùng cho request tiếp theo và ghi vào state', async () => {
  values.set('preferredGeminiModel', 'gemini-test');
  globalThis.fetch = async (_url, options) => {
    assert.equal(JSON.parse(options?.body as string).model_id, 'gemini-test');
    values.set('preferredGeminiModel', 'changed-during-request');
    return Response.json(backendResponse);
  };
  await handleAnalysisRequest(request, sender);
  assert.equal(getLiveAnalysisState(7)?.request?.model_id, 'gemini-test');
  assert.equal(values.get('preferredGeminiModel'), 'changed-during-request');
});

test('giữ metadata model và thông báo hết quota từ backend', async () => {
  const usage = { requested_model: 'a', extraction_model: 'b', assessment_model: 'b',
    fallbacks: [{ stage: 'extraction', model: 'a', reason: 'quota' }] };
  assert.deepEqual(mapAnalysisResponse({ ...backendResponse, model_usage: usage }).model_usage, usage);
  globalThis.fetch = async () => Response.json({ detail: 'Tất cả model chạm hạn mức' }, { status: 503 });
  await handleAnalysisRequest(request, sender);
  assert.equal(getLiveAnalysisState(7)?.error, 'Tất cả model chạm hạn mức');
});
