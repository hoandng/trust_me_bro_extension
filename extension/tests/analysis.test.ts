import assert from 'node:assert/strict';
import { afterEach, beforeEach, test } from 'node:test';
import {
  forgetAnalysisTab,
  getLiveAnalysisState,
  handleAnalysisRequest,
  retryAnalysisForTab,
} from '../src/features/analysis/background/handle-analysis';
import {
  mapAnalysisResponse,
  mapConfidenceLevel,
  resolvePublisherName,
  truncateSnippet,
} from '../src/features/analysis/background/map-response';
import {
  parseExplanation,
  renderExplanationSegments,
  stripExplanationMarkers,
} from '../src/features/analysis/explanation-parser';
import { getCachedModelCatalog } from '../src/features/analysis/model-preference';
import { buildShareSummary } from '../src/features/analysis/share-summary';
import { initAnalysisPanel } from '../src/features/analysis/sidepanel/controller';
import { renderAnalysisState } from '../src/features/analysis/sidepanel/render';
import { safeSourceUrl } from '../src/features/analysis/source-url';
import {
  getTabState,
  setTabState,
  subscribeToTabStates,
} from '../src/features/analysis/state-store';
import {
  FEEDBACK_ENDPOINT_ENABLED,
  isFeedbackEndpointEnabled,
  setFeedbackEndpointEnabled,
  SIDEPANEL_PATH,
} from '../src/shared/config';
import {
  isAnalysisTabMessage,
  isAnalyzeRequest,
  isSubmitFeedbackMessage,
} from '../src/shared/messages';
import type { AnalyzeRequestMessage, SubmitFeedbackMessage } from '../src/shared/messages';
import type { BackendAnalysisResponse, FeedbackReply } from '../src/features/analysis/types';

const originalFetch = globalThis.fetch;
const originalChrome = globalThis.chrome;
const originalDocument = globalThis.document;
const originalWindow = globalThis.window;
const originalOption = globalThis.Option;

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
  explanation: 'Tin [[+có nguồn xác nhận]] nhưng [[-sai ngày]].',
  sources: [
    {
      title: 'Nguồn tin',
      url: 'https://vnexpress.net/bai-viet-kiem-chung',
      publisher_name: 'vnexpress.net',
      stance: 'supports',
    },
  ],
  service_status: { gemini: 'ok', tavily: 'ok', factcheck: 'empty' },
};

// Mock DOM nhẹ để kiểm thử render.ts, explanation-parser.ts và controller.ts không cần trình duyệt.
class MockClassList {
  private set = new Set<string>();
  constructor(initial = '') {
    initial
      .split(/\s+/)
      .filter(Boolean)
      .forEach((c) => this.set.add(c));
  }
  add(...tokens: string[]) {
    tokens.forEach((t) => this.set.add(t));
  }
  remove(...tokens: string[]) {
    tokens.forEach((t) => this.set.delete(t));
  }
  contains(token: string): boolean {
    return this.set.has(token);
  }
  toggle(token: string, force?: boolean): boolean {
    const shouldHave = force !== undefined ? force : !this.set.has(token);
    if (shouldHave) this.set.add(token);
    else this.set.delete(token);
    return shouldHave;
  }
  toString(): string {
    return [...this.set].join(' ');
  }
}

class MockElement {
  tagName: string;
  id = '';
  value = '';
  disabled = false;
  href = '';
  target = '';
  rel = '';
  dataset: Record<string, string> = {};
  attributes = new Map<string, string>();
  children: MockElement[] = [];
  classList = new MockClassList();
  private _textContent = '';
  private eventListeners = new Map<string, Array<() => void>>();

  constructor(tagName: string, id = '', className = '') {
    this.tagName = tagName.toUpperCase();
    this.id = id;
    this.classList = new MockClassList(className);
  }

  get className(): string {
    return this.classList.toString();
  }
  set className(val: string) {
    this.classList = new MockClassList(val);
  }

  get textContent(): string {
    if (this.children.length === 0) return this._textContent;
    return this._textContent + this.children.map((c) => c.textContent).join('');
  }
  set textContent(val: string) {
    this._textContent = String(val ?? '');
    this.children = [];
  }

  appendChild(child: MockElement): MockElement {
    this.children.push(child);
    return child;
  }

  replaceChildren(...nodes: MockElement[]) {
    this._textContent = '';
    this.children = [...nodes];
  }

  add(option: MockElement) {
    this.appendChild(option);
  }

  setAttribute(name: string, val: string) {
    this.attributes.set(name, val);
  }

  getAttribute(name: string): string | null {
    return this.attributes.get(name) ?? null;
  }

  addEventListener(event: string, cb: () => void) {
    const list = this.eventListeners.get(event) ?? [];
    list.push(cb);
    this.eventListeners.set(event, list);
  }

  click() {
    if (this.disabled) return;
    for (const cb of this.eventListeners.get('click') ?? []) cb();
  }

  querySelectorAll(selector: string): MockElement[] {
    const cls = selector.startsWith('.') ? selector.slice(1) : '';
    const results: MockElement[] = [];
    const visit = (el: MockElement) => {
      for (const child of el.children) {
        if (cls && child.classList.contains(cls)) results.push(child);
        visit(child);
      }
    };
    visit(this);
    return results;
  }
}

function setupMockSidePanelDom() {
  const elements = new Map<string, MockElement>();
  const register = (tag: string, id: string, className = '') => {
    const el = new MockElement(tag, id, className);
    elements.set(id, el);
    return el;
  };

  register('button', 'btn-settings', 'btn-icon');
  register('section', 'settings-panel', 'card model-settings hidden');
  register('select', 'model-selector');
  register('p', 'model-hint');

  register('div', 'state-idle', 'state-container');
  register('div', 'state-loading', 'state-container hidden');
  register('p', 'loading-step-text');
  register('p', 'loading-text-preview');

  register('div', 'state-success', 'state-container hidden');
  register('div', 'result-verdict', 'verdict-banner');
  register('span', 'verdict-icon');
  register('h2', 'verdict-text');
  register('p', 'verdict-subtext', 'hidden');
  register('div', 'service-warning', 'warning-badge hidden');
  register('strong', 'result-confidence-text');

  const bars = register('div', 'confidence-bars');
  for (let i = 0; i < 3; i += 1) {
    bars.appendChild(new MockElement('span', '', 'certainty-bar'));
  }

  register('p', 'result-explanation');
  register('div', 'explanation-legend');
  register('strong', 'sources-heading');
  register('p', 'sources-neutral-note', 'hidden');
  register('ul', 'result-sources');

  register('button', 'btn-copy');
  register('p', 'copy-status');

  register('section', 'feedback-actions', 'hidden');
  const stars = register('div', 'feedback-stars');
  for (let r = 1; r <= 5; r += 1) {
    const btn = new MockElement('button', '', 'star-btn');
    btn.dataset.rating = String(r);
    btn.setAttribute('aria-pressed', 'false');
    stars.appendChild(btn);
  }
  register('textarea', 'feedback-comment');
  register('button', 'btn-submit-feedback');
  register('p', 'feedback-status');

  register('details', 'tech-details');
  register('p', 'model-usage');
  register('p', 'response-duration');
  register('p', 'success-text-preview');
  register('button', 'btn-read-more', 'hidden');

  register('div', 'state-error', 'state-container hidden');
  register('p', 'error-message');
  register('button', 'btn-retry');

  globalThis.Option = class MockOption extends MockElement {
    constructor(text = '', value = '') {
      super('option');
      this.textContent = text;
      this.value = value;
    }
  } as unknown as typeof Option;

  globalThis.document = {
    getElementById: (id: string) => elements.get(id) ?? null,
    createElement: (tag: string) => new MockElement(tag),
    createElementNS: (_ns: string, tag: string) => new MockElement(tag),
  } as unknown as Document;

  globalThis.window = {
    addEventListener: () => {},
    setInterval: globalThis.setInterval,
    clearInterval: globalThis.clearInterval,
  } as unknown as Window & typeof globalThis;

  return elements;
}

beforeEach(() => {
  values.clear();
  listeners.clear();
  setFeedbackEndpointEnabled(FEEDBACK_ENDPOINT_ENABLED);
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
    tabs: {
      query: async () => [{ id: 7 }],
      onActivated: { addListener: () => {} },
      onRemoved: { addListener: () => {} },
      onUpdated: { addListener: () => {} },
    },
    runtime: {
      getURL: (path: string) => `chrome-extension://mock/${path}`,
      sendMessage: async () => getLiveAnalysisState(7) ?? { status: 'idle' },
      onMessage: { addListener: (listener: MessageListener) => { messageListener = listener; } },
    },
  } as unknown as typeof chrome;
});

afterEach(async () => {
  setFeedbackEndpointEnabled(FEEDBACK_ENDPOINT_ENABLED);
  await Promise.all([forgetAnalysisTab(7), forgetAnalysisTab(8)]);
  globalThis.fetch = originalFetch;
  globalThis.chrome = originalChrome;
  globalThis.document = originalDocument;
  globalThis.window = originalWindow;
  globalThis.Option = originalOption;
});

test('chỉ nhận message có đúng hợp đồng phân tích và đánh giá 5 sao', () => {
  assert.equal(isAnalyzeRequest(request), true);
  assert.equal(isAnalyzeRequest({ ...request, payload: { text: 123 } }), false);
  assert.equal(isAnalyzeRequest({ ...request, tabId: '7' }), false);
  assert.equal(isAnalyzeRequest({ type: 'UNKNOWN' }), false);
  assert.equal(isAnalyzeRequest(null), false);
  assert.equal(isAnalysisTabMessage({ type: 'GET_ANALYSIS_STATE', tabId: 7 }), true);
  assert.equal(isAnalysisTabMessage({ type: 'RETRY_ANALYSIS', tabId: -1 }), false);

  const validFeedback: SubmitFeedbackMessage = {
    type: 'SUBMIT_ANALYSIS_FEEDBACK',
    tabId: 7,
    request_id: backendResponse.request_id!,
    rating: 5,
    comment: 'Rất rõ ràng',
  };
  assert.equal(isSubmitFeedbackMessage(validFeedback), true);
  assert.equal(isSubmitFeedbackMessage({ ...validFeedback, comment: undefined }), true);
  assert.equal(isSubmitFeedbackMessage({ ...validFeedback, rating: 0 }), false);
  assert.equal(isSubmitFeedbackMessage({ ...validFeedback, rating: 6 }), false);
  assert.equal(isSubmitFeedbackMessage({ ...validFeedback, comment: 'a'.repeat(501) }), false);
  // Tuyệt đối từ chối nếu có thêm trường ngoài hợp đồng như text hoặc page_url
  assert.equal(
    isSubmitFeedbackMessage({ ...validFeedback, text: 'Bài đăng riêng tư' }),
    false,
  );
  assert.equal(
    isSubmitFeedbackMessage({ ...validFeedback, page_url: 'https://facebook.com/post' }),
    false,
  );
});

test('parser giải thích: chuỗi thường, cân bằng, không cân bằng, lồng nhau, rỗng, ký hiệu giả và HTML', () => {
  // 1. Rỗng
  assert.deepEqual(parseExplanation(''), []);

  // 2. Chuỗi bình thường
  assert.deepEqual(parseExplanation('Thông tin đã được cơ quan chức năng xác nhận.'), [
    { text: 'Thông tin đã được cơ quan chức năng xác nhận.', status: 'plain' },
  ]);

  // 3. Ký hiệu cân bằng (xanh +, đỏ -, xám ?)
  assert.deepEqual(
    parseExplanation('Tin [[+đúng sự kiện]] nhưng [[-sai thời gian]] và [[?chưa rõ thiệt hại]].'),
    [
      { text: 'Tin ', status: 'plain' },
      { text: 'đúng sự kiện', status: 'confirmed' },
      { text: ' nhưng ', status: 'plain' },
      { text: 'sai thời gian', status: 'refuted' },
      { text: ' và ', status: 'plain' },
      { text: 'chưa rõ thiệt hại', status: 'unverified' },
      { text: '.', status: 'plain' },
    ],
  );

  // 4. Không cân bằng (thiếu đóng hoặc dư đóng) -> trả về plain text đã bỏ ký hiệu
  assert.deepEqual(parseExplanation('Tin [[+chưa đóng ngoặc'), [
    { text: 'Tin chưa đóng ngoặc', status: 'plain' },
  ]);
  assert.deepEqual(parseExplanation('Tin dư ngoặc đóng]] ở giữa'), [
    { text: 'Tin dư ngoặc đóng ở giữa', status: 'plain' },
  ]);

  // 5. Lồng nhau -> trả về plain text đã bỏ ký hiệu
  assert.deepEqual(parseExplanation('Tin [[+bên ngoài [[-bên trong]] lỗi]]'), [
    { text: 'Tin bên ngoài bên trong lỗi', status: 'plain' },
  ]);

  // 6. Quá 4 đoạn đánh dấu -> trả về plain text đã bỏ ký hiệu
  assert.deepEqual(
    parseExplanation('[[+Một]] [[-Hai]] [[?Ba]] [[+Bốn]] [[-Năm]]'),
    [{ text: 'Một Hai Ba Bốn Năm', status: 'plain' }],
  );

  // 7. Ký hiệu giả từ text người dùng đã bị backend vô hiệu hoá ("[ [+giả] ]")
  assert.deepEqual(parseExplanation('Người dùng viết [ [+đánh dấu giả] ] trong bài.'), [
    { text: 'Người dùng viết [ [+đánh dấu giả] ] trong bài.', status: 'plain' },
  ]);

  // 8. Nội dung chứa ký tự HTML phải giữ nguyên văn, dựng bằng createElement + textContent
  const elements = setupMockSidePanelDom();
  const container = elements.get('result-explanation')!;
  const htmlPayload = 'Chú ý [[+<script>alert("xss")</script>]] và [[-<img src=x onerror=alert(1)>]].';
  renderExplanationSegments(container as unknown as HTMLElement, htmlPayload, document);
  assert.equal(
    container.textContent,
    'Chú ý ✓ <script>alert("xss")</script> và ✗ <img src=x onerror=alert(1)>.',
  );
  // Chỉ tạo thẻ SPAN, không có thẻ SCRIPT hay IMG nào được tạo
  const allTags: string[] = [];
  const collectTags = (el: MockElement) => {
    for (const child of el.children) {
      allTags.push(child.tagName);
      collectTags(child);
    }
  };
  collectTags(container);
  assert.ok(allTags.every((t) => t === 'SPAN'));
  assert.equal(
    stripExplanationMarkers('Tin [[+đúng]] nhưng [[-sai]].'),
    'Tin đúng nhưng sai.',
  );
});

test('ánh xạ verdict, mức chắc chắn 3 vạch (không phần trăm), nhãn nguồn, tên báo và cắt đoạn trích', () => {
  // 1. Verdict mapping
  const expectedVerdicts = {
    likely_true: { conclusion: 'Có vẻ đúng', subtext: undefined },
    likely_false: { conclusion: 'Có vẻ sai sự thật', subtext: undefined },
    mixed: { conclusion: 'Đúng một phần', subtext: undefined },
    unverified: { conclusion: 'Chưa đủ bằng chứng', subtext: 'Đừng vội chia sẻ tin này.' },
    unknown_value: { conclusion: 'Chưa đủ bằng chứng', subtext: 'Đừng vội chia sẻ tin này.' },
  };
  for (const [verdict, expected] of Object.entries(expectedVerdicts)) {
    const mapped = mapAnalysisResponse({ ...backendResponse, verdict });
    assert.equal(mapped.conclusion, expected.conclusion);
    assert.equal(mapped.subtext, expected.subtext);
    assert.equal('confidence' in mapped, false);
  }

  // 2. Confidence level mapping (< 0.5 Thấp, < 0.75 Vừa, >= 0.75 Cao)
  assert.deepEqual(mapConfidenceLevel(0.0), { confidence_level: 'Thấp', confidence_bars: 1 });
  assert.deepEqual(mapConfidenceLevel(0.49), { confidence_level: 'Thấp', confidence_bars: 1 });
  assert.deepEqual(mapConfidenceLevel(0.5), { confidence_level: 'Vừa', confidence_bars: 2 });
  assert.deepEqual(mapConfidenceLevel(0.74), { confidence_level: 'Vừa', confidence_bars: 2 });
  assert.deepEqual(mapConfidenceLevel(0.75), { confidence_level: 'Cao', confidence_bars: 3 });
  assert.deepEqual(mapConfidenceLevel(0.95), { confidence_level: 'Cao', confidence_bars: 3 });

  // 3. Tên báo từ file JSON tĩnh (domain -> tên hiển thị), không có thì hiện domain
  assert.equal(
    resolvePublisherName(safeSourceUrl('https://vnexpress.net/tin-tuc'), 'vnexpress.net'),
    'VnExpress',
  );
  assert.equal(
    resolvePublisherName(safeSourceUrl('https://video.tuoitre.vn/bai-viet'), 'video.tuoitre.vn'),
    'Tuổi Trẻ',
  );
  assert.equal(
    resolvePublisherName(safeSourceUrl('https://news.example.com/check'), null, null),
    'news.example.com',
  );
  assert.equal(resolvePublisherName(safeSourceUrl('javascript:void(0)'), null, null), 'Nguồn bên ngoài');

  // 4. Cắt đoạn trích ở hết câu, tối đa khoảng 140 ký tự
  const twoSentences =
    'Câu đầu tiên dài vừa phải. Câu thứ hai kết thúc trọn vẹn. ' +
    'Câu thứ ba rất dài khiến tổng độ dài của đoạn trích vượt quá giới hạn một trăm bốn mươi ký tự quy định.';
  assert.equal(
    truncateSnippet(twoSentences),
    'Câu đầu tiên dài vừa phải. Câu thứ hai kết thúc trọn vẹn.',
  );
  const singleLongSentence =
    'Đây là một câu đơn rất dài không có dấu chấm câu ở giữa vượt quá giới hạn một trăm bốn mươi ký tự nên buộc phải cắt ở khoảng trắng cuối cùng hợp lệ';
  const truncatedSingle = truncateSnippet(singleLongSentence);
  assert.ok(truncatedSingle.length <= 140);
  assert.ok(truncatedSingle.endsWith('…'));

  // 5. Nhãn nguồn (Ủng hộ, Phản bác, Liên quan) và cờ all_sources_neutral
  const { sources, all_sources_neutral } = mapAnalysisResponse({
    ...backendResponse,
    sources: [
      {
        title: 'Bài báo',
        url: 'https://www.reuters.com/article',
        publisher: 'reuters.com',
        published_date: '2026-11-10',
        stance: 'supports',
      },
      {
        title: 'Bài kiểm chứng',
        url: 'https://news.example.com/check',
        published_date: 'Tue, 10 Nov 2026 20:00:00 GMT',
        stance: 'refutes',
      },
      {
        title: '<img src=x>',
        url: 'javascript:void(0)',
        publisher_name: null,
        published_date: '2026-02-31',
        stance: 'unsupported',
      },
    ],
  });
  assert.equal(all_sources_neutral, false);
  assert.deepEqual(
    sources.map((s) => [s.publisher, s.publishedDate, s.stance, s.stanceLabel]),
    [
      ['Reuters', '10/11/2026', 'supports', 'Ủng hộ'],
      ['news.example.com', '11/11/2026', 'refutes', 'Phản bác'],
      ['Nguồn bên ngoài', undefined, 'neutral', 'Liên quan'],
    ],
  );
  assert.equal(sources[2].url, '');
  assert.equal(sources[2].title, '<img src=x>');

  const neutralOnly = mapAnalysisResponse({
    ...backendResponse,
    sources: [{ title: 'Tin liên quan', url: 'https://vtv.vn/tin-1', stance: 'neutral' }],
  });
  assert.equal(neutralOnly.all_sources_neutral, true);
  assert.equal(neutralOnly.sources[0].publisher, 'VTV');
  assert.equal(neutralOnly.sources[0].stanceLabel, 'Liên quan');
});

test('bản chia sẻ loại bỏ ký hiệu đánh dấu, lấy tối đa hai lý do và hai URL nguồn', () => {
  const result = mapAnalysisResponse({
    ...backendResponse,
    verdict: 'likely_false',
    explanation: '[[+Nguồn thứ nhất]] bác bỏ claim. [[-Số liệu không khớp]]. Lý do thứ ba.',
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
  const echoed = buildShareSummary(
    { ...result, explanation: request.payload.text, sources: [] },
    request.payload,
  );
  assert.ok(!echoed.includes(request.payload.text));
  assert.ok(!echoed.includes('Nguồn tham khảo'));
});

test('cờ FEEDBACK_ENDPOINT_ENABLED = false chặn gửi mạng; khi bật gửi đúng {request_id, rating, comment}', async () => {
  await import('../src/entrypoints/background');
  assert.ok(messageListener);
  const listener = messageListener;
  const panel = { url: chrome.runtime.getURL(SIDEPANEL_PATH) };
  globalThis.fetch = async () => Response.json(backendResponse);
  await handleAnalysisRequest(request, sender);

  const message: SubmitFeedbackMessage = {
    type: 'SUBMIT_ANALYSIS_FEEDBACK',
    tabId: 7,
    request_id: backendResponse.request_id!,
    rating: 4,
    comment: 'Nguồn đối chiếu tốt',
  };

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

  // Khi cờ FEEDBACK_ENDPOINT_ENABLED = false -> chặn gửi mạng, không khóa state.feedback
  setFeedbackEndpointEnabled(false);
  assert.equal(isFeedbackEndpointEnabled(), false);
  const disabledReply = await send(message);
  assert.deepEqual(disabledReply, { ok: false, error: 'Tính năng đánh giá sẽ sớm có' });
  assert.equal(posts, 0);
  assert.equal(getLiveAnalysisState(7)?.feedback, undefined);

  // Mặc định FEEDBACK_ENDPOINT_ENABLED = true: gửi đúng {request_id, rating, comment}
  setFeedbackEndpointEnabled(FEEDBACK_ENDPOINT_ENABLED);
  assert.equal(isFeedbackEndpointEnabled(), true);
  assert.equal(
    listener(message, { ...sender, url: request.payload.page_url }, () => {
      assert.fail('Message from the page should be ignored');
    }),
    undefined,
  );
  assert.equal(
    (await send({ ...message, request_id: '96822b5b-4e4a-4218-9e78-8d793f9770a6' })).ok,
    false,
  );
  assert.equal(posts, 0);

  replyStatus = 429;
  const failed = await send(message);
  assert.deepEqual(failed, { ok: false, error: 'Chưa gửi được phản hồi. Hãy thử lại sau.' });
  assert.equal(getLiveAnalysisState(7)?.feedback, undefined);

  replyStatus = 204;
  assert.deepEqual(await send(message), { ok: true });
  assert.deepEqual(await send(message), { ok: true });
  assert.equal(posts, 2);
  assert.deepEqual(getLiveAnalysisState(7)?.feedback, {
    request_id: message.request_id,
    rating: 4,
    comment: 'Nguồn đối chiếu tốt',
  });
  assert.deepEqual(bodies[1], {
    request_id: message.request_id,
    rating: 4,
    comment: 'Nguồn đối chiếu tốt',
  });
});

test('mở panel và render kết quả không gọi fetch; chỉ tải model khi mở Cài đặt và cache vào session', async () => {
  const elements = setupMockSidePanelDom();
  let fetchCalls = 0;
  globalThis.fetch = async () => {
    fetchCalls += 1;
    throw new Error('Không được gọi fetch khi mở panel hoặc render kết quả');
  };

  // Mở panel ở trạng thái idle -> 0 fetch
  await initAnalysisPanel();
  assert.equal(fetchCalls, 0);

  // Render kết quả phân tích -> 0 fetch, không hiện %, hiện đúng thời gian phản hồi và lời nhắn cờ feedback tắt
  const mapped = mapAnalysisResponse(backendResponse);
  mapped.duration_ms = 420;
  renderAnalysisState({
    status: 'success',
    request: request.payload,
    response: mapped,
  });
  assert.equal(fetchCalls, 0);
  assert.equal(elements.get('verdict-text')?.textContent, 'Có vẻ đúng');
  assert.equal(elements.get('result-confidence-text')?.textContent, 'Cao');
  assert.ok(!elements.get('result-confidence-text')?.textContent.includes('%'));
  assert.equal(elements.get('sources-heading')?.textContent, 'Nguồn liên quan (1)');
  assert.equal(elements.get('response-duration')?.textContent, '420 ms');

  // Khi người dùng bấm nút Cài đặt mở mục Cài đặt lần đầu -> tải danh sách model và lưu vào chrome.storage.session
  let modelFetchCount = 0;
  globalThis.fetch = async (url) => {
    modelFetchCount += 1;
    assert.equal(url, 'http://127.0.0.1:8000/api/v1/models');
    return Response.json({
      default_model: 'gemini-3.1-flash-lite',
      models: ['gemini-3.1-flash-lite', 'gemini-3.5-flash'],
    });
  };

  elements.get('btn-settings')!.click();
  await new Promise<void>((resolve) => setImmediate(resolve));
  assert.equal(modelFetchCount, 1);
  assert.deepEqual(await getCachedModelCatalog(), {
    default_model: 'gemini-3.1-flash-lite',
    models: ['gemini-3.1-flash-lite', 'gemini-3.5-flash'],
  });

  // Đóng và mở lại Cài đặt hoặc khởi tạo lại panel trong cùng session -> đọc từ session cache, 0 fetch mới
  elements.get('btn-settings')!.click();
  elements.get('btn-settings')!.click();
  await initAnalysisPanel();
  elements.get('btn-settings')!.click();
  await new Promise<void>((resolve) => setImmediate(resolve));
  assert.equal(modelFetchCount, 1);
});

test('background vẫn dùng preferredGeminiModel từ chrome.storage.local dù chưa mở mục Cài đặt', async () => {
  setupMockSidePanelDom();
  values.set('preferredGeminiModel', 'gemini-saved-in-local');

  // Mở panel nhưng không bấm vào Cài đặt
  globalThis.fetch = async () => {
    throw new Error('Panel open must not call fetch');
  };
  await initAnalysisPanel();

  // Thực hiện phân tích ở background -> vẫn lấy đúng model đã lưu trong chrome.storage.local
  let sentModelId: string | undefined;
  globalThis.fetch = async (_url, options) => {
    sentModelId = JSON.parse(options?.body as string).model_id;
    values.set('preferredGeminiModel', 'changed-during-request');
    return Response.json(backendResponse);
  };
  await handleAnalysisRequest(request, sender);
  assert.equal(sentModelId, 'gemini-saved-in-local');
  assert.equal(getLiveAnalysisState(7)?.request?.model_id, 'gemini-saved-in-local');
  assert.equal(typeof getLiveAnalysisState(7)?.response?.duration_ms, 'number');
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
  finishFetch(
    Response.json({
      ...backendResponse,
      explanation: request.payload.text,
      sources: [{ title: request.payload.text, url: request.payload.page_url }],
    }),
  );
  await pending;
  assert.deepEqual(await getTabState(7), {
    status: 'success',
    request_id: backendResponse.request_id,
  });
  assert.equal(getLiveAnalysisState(7)?.response?.confidence_level, 'Cao');
  assert.equal(getLiveAnalysisState(7)?.response?.confidence_bars, 3);
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

test('giữ metadata model và thông báo hết quota từ backend', async () => {
  const usage = {
    requested_model: 'a',
    extraction_model: 'b',
    assessment_model: 'b',
    fallbacks: [{ stage: 'extraction', model: 'a', reason: 'quota' }],
  };
  assert.deepEqual(mapAnalysisResponse({ ...backendResponse, model_usage: usage }).model_usage, usage);
  globalThis.fetch = async () => Response.json({ detail: 'Tất cả model chạm hạn mức' }, { status: 503 });
  await handleAnalysisRequest(request, sender);
  assert.equal(getLiveAnalysisState(7)?.error, 'Tất cả model chạm hạn mức');
});
