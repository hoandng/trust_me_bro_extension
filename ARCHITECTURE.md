# ARCHITECTURE.md

> Dự án: **Trust Me Bro** — Browser Extension (Manifest V3) + FastAPI Orchestrator Backend kiểm chứng độ tin cậy bài đăng mạng xã hội.

---

## 1. Kiến trúc tổng quan

Hệ thống áp dụng mô hình **Client–Server**:

- **Client (Chrome Extension MV3):** Chỉ chịu trách nhiệm bắt tương tác trên DOM (Facebook, Reddit), quản lý trạng thái hiển thị theo từng tab và render kết quả trong Side Panel.
- **Server (FastAPI Backend):** Đóng vai trò **Orchestrator** giữ toàn bộ API key của bên thứ ba, kiểm soát xác thực, giới hạn tốc độ, cache, điều phối gọi các dịch vụ AI/tìm kiếm, hậu xử lý kết quả và lưu số liệu vận hành.

```text
[Facebook / Reddit DOM]
   │ bôi đen (20–2000 ký tự) hoặc nút bài viết Reddit (/comments/)
   ▼
[Content Script: selection-controller + adapters + FloatingButton]
   │ chrome.runtime.sendMessage (ANALYZE_REQUEST)
   ▼
[Background Service Worker: background.ts + handle-analysis.ts]
   │ giữ state đầy đủ trong RAM (tabRuns)
   │ ghi metadata {status, request_id} vào chrome.storage.session
   │ HTTP POST /api/v1/analyze (X-API-Key, timeout 60s)
   ▼
[FastAPI Backend]
   ├─ Security & Rate Limit Middleware / Dependencies (IP, Key, Global)
   ├─ SQLite Cache Lookup (analysis_cache)
   ├─ AnalysisOrchestrator (deadline mặc định 25s)
   │     ├─ Stage 0: GeminiService.extract_claims (Interactions API)
   │     ├─ Stage 1: FactCheckService + TavilySearchService (song song)
   │     └─ Stage 2: Source Ranking + GeminiService.assess + Post-processing
   └─ SQLite Metrics (analysis_metrics, feedback) & Cache Save
   │
   ▼ JSON AnalyzeResponse
[Background Service Worker] ──map-response.ts──► [chrome.storage.session]
                                                         │ onChanged
                                                         ▼
                                            [Side Panel: controller + render]
                                            (đọc state đầy đủ từ RAM qua GET_ANALYSIS_STATE)
```

**Lý do chọn kiến trúc này:**
- **Bảo mật API key:** Toàn bộ key của Gemini, Tavily và Google Fact Check chỉ tồn tại trên backend; mã extension không chứa bí mật nhà cung cấp.
- **Dễ mở rộng nền tảng:** Logic bóc tách DOM được cô lập trong các `PlatformAdapter` của extension; bổ sung mạng xã hội mới không đòi hỏi sửa pipeline AI ở backend.
- **Dễ mở rộng nguồn kiểm chứng:** Tách `services/` khỏi `orchestrator/` giúp thêm/bớt nhà cung cấp bằng chứng hoặc thay đổi quy tắc tổng hợp độc lập với giao diện người dùng.

---

## 2. Browser Extension (Client)

### 2.1. Cấu trúc thư mục & Công nghệ

- **Công nghệ:** TypeScript `strict`, HTML/CSS và DOM thuần (không framework UI), Vite + plugin tạo `manifest.json` nội bộ trong `extension/vite.config.ts`.
- **Tổ chức theo tính năng (Feature-based Modular Architecture):**

```text
extension/
├── src/
│   ├── entrypoints/
│   │   ├── background.ts               # Listener runtime/tabs, phân quyền sender, điều phối
│   │   ├── content.ts                  # Khởi tạo selection controller trên trang web
│   │   └── sidepanel/
│   │       ├── index.html              # Khung DOM Side Panel
│   │       └── index.ts                # Khởi chạy controller của Side Panel
│   ├── features/analysis/
│   │   ├── types.ts                    # Kiểu request, response backend/UI, state, feedback
│   │   ├── state-store.ts              # Quy ước key tabState_<tabId> trong session storage
│   │   ├── model-preference.ts         # Model ưu tiên (local) & cache danh sách model (session)
│   │   ├── explanation-parser.ts       # Parser an toàn cho đánh dấu [[+...]], [[-...]], [[?...]]
│   │   ├── publisher-names.json        # Ánh xạ domain -> tên hiển thị báo chí/tổ chức kiểm chứng
│   │   ├── share-summary.ts            # Tạo bản tóm tắt chia sẻ, chống rò rỉ text/URL gốc
│   │   ├── source-url.ts               # Xác thực URL HTTP(S) không chứa thông tin đăng nhập
│   │   ├── background/
│   │   │   ├── handle-analysis.ts      # Quản lý RAM tabRuns, loading -> API -> success/error
│   │   │   ├── analysis-api.ts         # Gọi POST /api/v1/analyze và ánh xạ kết quả
│   │   │   ├── handle-feedback.ts      # Xử lý gửi feedback (hiện khóa sau cờ cấu hình)
│   │   │   └── map-response.ts         # Chuẩn hóa verdict, mức chắc chắn 3 vạch, nguồn, ngày
│   │   ├── content/
│   │   │   ├── selection-controller.ts # Debounce 150ms sự kiện chọn văn bản & ẩn/hiện nút nổi
│   │   │   ├── adapters/
│   │   │   │   ├── platform-adapter.ts # Interface PlatformAdapter
│   │   │   │   ├── index.ts            # Registry chọn adapter theo URL
│   │   │   │   ├── facebook-adapter.ts # Hỗ trợ bôi đen văn bản 20–2000 ký tự trên Facebook
│   │   │   │   └── reddit-adapter.ts   # Bôi đen + nút "Kiểm chứng bài viết" ở /comments/
│   │   │   └── ui/
│   │   │       ├── floating-button.ts  # Nút nổi đặt trong closed Shadow DOM (inline styles)
│   │   │       └── floating-button.css # Style tham chiếu (hiện chưa được import)
│   │   └── sidepanel/
│   │       ├── controller.ts           # Đồng bộ theo tab, tải lười catalog model, retry, feedback
│   │       ├── render.ts               # Dựng DOM bằng textContent/createElement, loading, tech details
│   │       └── index.css               # Hệ thống token màu & layout Side Panel
│   ├── infrastructure/
│   │   ├── api/backend-client.ts       # HTTP client (X-API-Key, timeout 60s, chuẩn hóa lỗi)
│   │   └── storage/session-store.ts    # Wrapper chrome.storage.session
│   └── shared/
│       ├── config.ts                   # SIDEPANEL_PATH & cờ FEEDBACK_ENDPOINT_ENABLED
│       └── messages.ts                 # Hợp đồng & type guard kiểm tra message đầu vào
├── public/icons/                       # Icon 16, 48, 128px
├── tests/
│   ├── analysis.test.ts                # Unit/module test với mock Chrome & fetch
│   └── run-tests.mjs                   # Runner build TS qua Vite và chạy bằng node --test
└── vite.config.ts                      # Tạo dist/manifest.json và đóng gói 3 entrypoint
```

### 2.2. Quy tắc phụ thuộc

- Chiều phụ thuộc chuẩn: `entrypoints/` → `features/` → `infrastructure/`.
- `entrypoints/` chỉ đăng ký Chrome listener và gọi hàm khởi tạo; không chứa logic nghiệp vụ.
- Ngữ cảnh tách biệt: module `background/` không import DOM của `content/` hoặc `sidepanel/`; `content/` không import HTTP client hay logic `background/`.
- `shared/messages.ts` chỉ dùng `import type` từ `features/` để không kéo code thực thi sang ngữ cảnh khác.
- `infrastructure/` không import ngược từ `features/` hoặc `entrypoints/`.

### 2.3. Luồng xử lý phía Extension

1. **Kích hoạt phân tích trên trang (`content/`):**
   - `selection-controller.ts` gọi `getAdapterForUrl()` chọn `RedditAdapter` hoặc `FacebookAdapter`.
   - Khi bôi đen đoạn văn bản **20–2000 ký tự** (debounce 150ms), `FloatingButton` (trong closed Shadow DOM) hiển thị phía trên vùng chọn và gửi `ANALYZE_REQUEST` gồm `{ text, platform, page_url }`.
   - Riêng `RedditAdapter.init()` theo dõi `<shreddit-post>` bằng `IntersectionObserver`, `MutationObserver`, `popstate` và `click`. Khi URL chứa `/comments/`, adapter bóc tách tiêu đề (`[slot="title"]` / `post-title`), thân bài (`[slot="text-body"]` hoặc `#-post-rtjson-content` / `div[id*="rtjson"]` trong `shadowRoot`) và URL bài báo (`content-href`); gắn viền nhận diện và chèn nút **"Kiểm chứng bài viết"**. Nếu văn bản trích được `< 20` ký tự thì bù khoảng trắng cho đủ 20, nếu `> 2000` ký tự thì cắt còn 2000 trước khi gửi `ANALYZE_REQUEST`.
2. **Điều phối tại Service Worker (`background.ts` & `handle-analysis.ts`):**
   - `background.ts` kiểm tra hợp đồng đầu vào qua `isAnalyzeRequest()`. Các message nội bộ từ Side Panel (`GET_ANALYSIS_STATE`, `RETRY_ANALYSIS`, `SUBMIT_ANALYSIS_FEEDBACK`) chỉ được chấp nhận khi `sender.url === chrome.runtime.getURL(SIDEPANEL_PATH)`.
   - `handleAnalysisRequest()` gọi `chrome.sidePanel.open({ tabId })` ngay trong ngữ cảnh user gesture (nếu trình duyệt chặn, gắn badge `!` đỏ lên icon tiện ích), xóa badge khi hợp lệ và cập nhật trạng thái `loading` vào `chrome.storage.session` (`tabState_<tabId>`).
   - Snapshot `preferredGeminiModel` từ `chrome.storage.local` một lần cho lượt chạy; gọi `POST /api/v1/analyze` với `X-API-Key` và timeout 60 giây, đồng thời đo `duration_ms` phía client.
   - Kết quả trả về được chuẩn hóa qua `map-response.ts`:
     - Chuyển `verdict` sang nhãn và câu kết luận tiếng Việt (`Có vẻ đúng`, `Có vẻ sai sự thật`, `Đúng một phần`, `Chưa đủ bằng chứng` kèm subtext cảnh báo).
     - Quy đổi `confidence_score` thành **3 mức và 3 vạch chắc chắn** (không hiển thị phần trăm): `< 0.5` → `Thấp` (1 vạch), `0.5 ≤ score < 0.75` → `Vừa` (2 vạch), `≥ 0.75` → `Cao` (3 vạch).
     - Chuẩn hóa tên nguồn bằng `publisher-names.json` trước, sau đó dùng giá trị từ backend hoặc hostname.
     - Lọc URL chỉ giữ `http:` / `https:` không chứa credentials (`safeSourceUrl`), cắt snippet khoảng 140 ký tự theo ranh giới câu, định dạng ngày (`vi-VN`, múi giờ `Asia/Ho_Chi_Minh`) và ánh xạ stance (`Ủng hộ`, `Phản bác`, `Liên quan`).
   - Toàn bộ state đầy đủ (`request`, `response`, `error`, `feedback`) chỉ giữ trong RAM của Service Worker (`tabRuns` Map); `chrome.storage.session` chỉ lưu `{ status, request_id? }`. Khi tab đóng hoặc điều hướng (`tabs.onRemoved` / `tabs.onUpdated`), `forgetAnalysisTab()` xóa cả RAM lẫn session key.
3. **Hiển thị & Tương tác tại Side Panel (`controller.ts` & `render.ts`):**
   - Lắng nghe thay đổi của `chrome.storage.session` và sự kiện chuyển tab (`tabs.onActivated`, `tabs.onUpdated`); lấy dữ liệu chi tiết từ RAM của background bằng `GET_ANALYSIS_STATE`.
   - **Tải lười danh sách model:** Khi khởi tạo Side Panel **không** gọi API. Chỉ khi người dùng bấm mở mục Cài đặt (`#btn-settings`) lần đầu, panel mới gọi `GET /api/v1/models` (nếu chưa có trong `chrome.storage.session` key `geminiModelCatalog`) và đổ danh sách model vào `<select>`. Lựa chọn được lưu vào `chrome.storage.local` (`preferredGeminiModel`).
   - **Giải thích có đánh dấu:** `explanation-parser.ts` phân tích tối đa 4 đoạn đánh dấu không lồng nhau `[[+...]]` (`✓`), `[[-...]]` (`✗`), `[[?...]]` (`?`) và dựng DOM bằng `createElement` + `textContent`. Nếu sai cú pháp hoặc vượt giới hạn, parser tự loại bỏ ký hiệu và hiển thị văn bản thuần.
   - **Thử lại & Chia sẻ:** Nút **Thử lại** gửi `RETRY_ANALYSIS` dùng lại payload trong RAM kèm model ưu tiên mới nhất. Nút **Sao chép để chia sẻ** (`share-summary.ts`) bỏ ký hiệu đánh dấu, chặn lặp lại văn bản/URL bài gốc, lấy tối đa 2 câu giải thích (≤ 160 ký tự/câu) và tối đa 2 URL nguồn HTTP(S) khác nhau kèm disclaimer.
   - **Trạng thái hiện tại của Feedback UI:** Giao diện hiển thị khung đánh giá 5 sao + nhận xét (≤ 500 ký tự), nhưng cờ `FEEDBACK_ENDPOINT_ENABLED` trong `shared/config.ts` đang đặt là `false` (chặn gửi mạng ở cả `controller.ts` lẫn `handle-feedback.ts`) do backend `/api/v1/feedback` hiện nhận `{ request_id, helpful, reason }` thay vì `{ request_id, rating, comment }`.

---

## 3. Backend API (Server)

### 3.1. Cấu trúc thư mục

```text
backend/
├── app/
│   ├── main.py                         # Khởi tạo FastAPI, lifespan, security middleware, CORS
│   ├── api/
│   │   ├── deps.py                     # Auth (API/Admin key), proxy IP extraction, rate limits, DI
│   │   └── v1/
│   │       ├── analyze.py              # POST /api/v1/analyze, GET /api/v1/models
│   │       └── metrics.py              # POST /api/v1/feedback, GET /api/v1/stats/summary
│   ├── core/
│   │   ├── config.py                   # Pydantic BaseSettings đọc env & validation
│   │   ├── rate_limit.py               # Rate limiter theo IP, key và global daily trong RAM
│   │   ├── logging.py                  # JSONFormatter ẩn bí mật, tắt INFO của httpx
│   │   ├── metrics.py                  # MetricsStore (SQLite), ContextVar, ước tính chi phí USD
│   │   ├── analysis_cache.py           # AnalysisCache (SQLite) có TTL & chặn lộ dữ liệu gốc
│   │   ├── source_ranking.py           # Xếp hạng tier nguồn & ánh xạ display_names
│   │   └── trusted_domains.json        # Danh sách tier1, tier2 và display_names
│   ├── prompts/
│   │   └── gemini_prompts.py           # System prompts cho Stage 0 (Extract) & Stage 2 (Assess)
│   ├── services/
│   │   ├── base_service.py             # Abstract BaseService & decorator safe_execute
│   │   ├── factcheck_service.py        # Google Fact Check Tools API + bảng chuẩn hóa rating EN/VI
│   │   ├── tavily_service.py           # Tavily Search API (news -> general fallback)
│   │   ├── gemini_service.py           # Gemini Interactions API + sanitize markers + URL filter
│   │   └── gemini_model_pool.py        # Cooldown theo model trong process khi gặp 429
│   ├── orchestrator/
│   │   └── analysis_orchestrator.py    # Điều phối pipeline 3 giai đoạn, deadline & hậu xử lý
│   └── schemas/
│       ├── internal.py                 # AnalysisContext, ServiceResult
│       ├── request.py                  # AnalyzeRequest (text, platform, page_url, lang, model_id, bypass_cache)
│       └── response.py                 # AnalyzeResponse, Source, ServiceStatus, ModelUsage
├── data/metrics.db                     # File SQLite runtime (nằm trong .gitignore)
├── tests/                              # Pytest unit, integration, security, cache, benchmark, e2e
├── Dockerfile
├── .env.example
└── requirements.txt
```

### 3.2. Lifespan & Quản lý kết nối

Tại startup, `lifespan()` trong `main.py` khởi tạo một lần mỗi worker:
- `MetricsStore` và `AnalysisCache` trên cùng file SQLite (`METRICS_DB_PATH`, mặc định `backend/data/metrics.db`).
- Một `httpx.AsyncClient(timeout=10.0)` dùng chung cho `FactCheckService` và `TavilySearchService`.
- Một `GeminiService` giữ `genai.Client` dùng chung (`HttpOptions(retry_options=HttpRetryOptions(attempts=0), timeout=15000)` để tự xử lý xoay vòng quota ở tầng ứng dụng).
- Một `AnalysisOrchestrator` lưu trong `app.state.orchestrator`. Các client được đóng sạch khi shutdown.

### 3.3. Danh sách Endpoint

| Endpoint | Xác thực | Giới hạn tốc độ | Chức năng |
|---|---|---|---|
| `GET /health` | Không | Không | Kiểm tra tiến trình FastAPI (`{"status": "ok"}`). |
| `GET /api/v1/models` | `X-API-Key` | Không | Trả `default_model` và danh sách `models` đã loại trùng. |
| `POST /api/v1/analyze` | `X-API-Key` | IP/phút, Key/ngày (khi miss cache), Global/ngày | Phân tích độ tin cậy văn bản 20–2000 ký tự (`facebook`, `reddit`, `x`). |
| `POST /api/v1/feedback` | `X-API-Key` | Dùng chung IP/Key/Global với `/analyze` | Ghi/cập nhật phản hồi (`request_id`, `helpful`, `reason`), trả `204` hoặc `404`. |
| `GET /api/v1/stats/summary` | `X-Admin-API-Key` | Không | Trả tổng lượt, tỷ lệ verdict, độ trễ TB/p95, chi phí TB và tỷ lệ helpful. |

### 3.4. Luồng xử lý tại `AnalysisOrchestrator`

Pipeline chạy dưới một **ngân sách thời gian đơn điệu (monotonic deadline)** mặc định `25.0` giây (`ANALYSIS_TIMEOUT_SECONDS`). Khi quá ngân sách ở bất kỳ bước nào, orchestrator hủy tác vụ chờ và trả `verdict="unverified"` (`confidence_score=0.0`) kèm các nguồn đã thu được.

1. **Stage 0 — Trích xuất & Lọc (`extract_claims`):**
   - Timeout tại orchestrator: `min(deadline, now + 20s)` (mỗi lượt SDK tối đa 15s, tối đa 2 lần thử nếu lỗi không phải `429` hoặc lỗi validate JSON).
   - Văn bản người dùng được trung hòa chuỗi `[[` / `]]` và bọc trong `<post>...</post>`.
   - Trả về `main_claim`, `search_queries` (tối đa 3), `detected_lang`, `is_checkable`.
   - Nếu trích xuất rỗng/lỗi → trả ngay `unverified` (`0.0`, `service_status.gemini="error"`). Nếu `is_checkable=false` → trả ngay `unverified` (`0.0`) để tiết kiệm chi phí tra cứu.
2. **Stage 1 — Thu thập bằng chứng song song:**
   - Lấy tối đa `SEARCH_QUERY_LIMIT` truy vấn đầu tiên (mặc định 2, giới hạn cứng 1–2), loại bỏ rỗng và trùng; nếu không còn truy vấn thì dùng `main_claim`.
   - Chạy song song từng cặp `(provider, query)` trong `asyncio.wait(..., timeout=min(remaining, 15.0))`, mỗi lượt gọi service bọc bởi `@safe_execute(timeout_seconds=10.0)`:
     - **`FactCheckService`:** Gọi Google Fact Check Tools API `claims:search` (`pageSize=10`, `languageCode=ctx.lang`). Nếu rỗng và có `ctx.lang`, thử lại 1 lần bỏ `languageCode`. Chuẩn hóa `textualRating` theo bảng từ điển tiếng Anh & tiếng Việt (`RATING_GROUPS`), gán `stance` và khóa `original_stance` (`frozen=True`) cùng `claim_text`.
     - **`TavilySearchService`:** Gọi `POST https://api.tavily.com/search` (`search_depth="basic"`, `max_results=5`, `include_published_date=True`, `include_usage=True`, kèm `include_domains`/`exclude_domains` nếu cấu hình). Thử `topic="news"` trước; nếu rỗng thì fallback sang `topic="general"`. Cắt `snippet` còn tối đa 300 ký tự.
3. **Gộp, Xếp hạng & Kiểm tra ngưỡng bằng chứng:**
   - Gộp nguồn theo thứ tự Fact Check trước, Tavily sau; khi trùng URL thì giữ bản Fact Check để bảo toàn `original_stance`.
   - Xếp hạng qua `source_ranking.py` theo thứ tự `tier1` → `tier2` → `default` (đọc từ `trusted_domains.json`, so khớp theo ranh giới hostname) rồi lấy tối đa **8 nguồn**. Hiện `trusted_domains.json` cấu hình `tier1` (`reuters.com`, `who.int`, `factcheck.org`) và `tier2` (`britannica.com`).
   - Nếu không có nguồn nào → trả `unverified` (`confidence_score=0.3`). Nếu hết deadline trước Stage 2 → trả `unverified` (`0.0`) với `sorted_sources`.
4. **Stage 2 — Đánh giá tổng hợp (`assess`) & Hậu xử lý:**
   - Timeout tại orchestrator: `min(deadline, now + 20s)`, tối đa 2 lần thử.
   - Truyền cho Gemini: ngày hiện tại theo múi giờ `Asia/Ho_Chi_Minh`, `claim`, `<post>`, và tối đa 8 nguồn kèm `source_tier`, `published_date`, `source_type`, `claim_text`, `original_stance` (đã trung hòa `[[` / `]]`).
   - Prompt yêu cầu Gemini đánh giá chỉ dựa trên bằng chứng, đối chiếu ngày sự kiện để phát hiện tin cũ đăng lại, sinh giải thích tiếng Việt ≤ 60 từ có tối đa 4 đánh dấu `[[+...]]` / `[[-...]]` / `[[?...]]`, trả `factcheck_match=true` chỉ khi `claim_text` của FactCheck khớp đúng mệnh đề với claim người dùng.
   - Backend validate JSON qua Pydantic, lọc bỏ URL ảo giác không thuộc tập 8 nguồn, và chuẩn hóa/dọn đánh dấu qua `sanitize_explanation_markers()`.
   - **Quy tắc hậu xử lý tại Orchestrator:**
     1. Chỉ cập nhật `stance` từ Gemini cho nguồn thuộc Tavily (không ghi đè nguồn Fact Check hoặc nguồn trùng URL với Fact Check).
     2. **Ưu tiên Fact Check:** Chỉ xét nguồn Fact Check đầu tiên (`factcheck_sources[:1]`) nếu nguồn này nằm trong top-8 `sorted_sources`, bước `assess` thành công, `claim_text` không rỗng và Gemini trả `factcheck_match=True`. Nếu `original_stance` là `supports`/`refutes` mà verdict chưa tương ứng `likely_true`/`likely_false`, ghi đè verdict và nâng `confidence_score = max(confidence_score, 0.8)`.
     3. **Ràng buộc nhất quán:** `likely_true` / `likely_false` phải có `confidence_score ≥ 0.5`; `unverified` bị giới hạn `confidence_score ≤ 0.4`.
   - Trước khi trả response ở `/analyze`, backend ghi đè `source.publisher` bằng `source_display_name(source.url)` (từ `display_names` trong `trusted_domains.json`) cho cả cache miss và cache hit.

### 3.5. Chọn model Gemini & Xoay vòng Quota

- `settings.available_gemini_models` ghép `[GEMINI_MODEL, *GEMINI_MODELS]` và loại bỏ tên trùng theo thứ tự. Mặc định `GEMINI_MODEL=gemini-3.1-flash-lite`. Các model bắt đầu bằng `gemini-3` được cấu hình `{"thinking_level": "low"}`.
- Mỗi lượt phân tích dùng một `ModelUsage(requested_model=...)` riêng biệt (an toàn với request đồng thời). Nếu `model_id` nằm ngoài danh sách cấu hình, FastAPI trả HTTP `422`.
- `GeminiService._create()` duyệt vòng tròn bắt đầu từ `requested_model`. `GeminiModelPool` giữ thời gian cooldown trên RAM theo từng process:
  - Bỏ qua model đang cooldown (ghi nhận vào `model_usage.fallbacks`).
  - Chỉ HTTP `429` từ Gemini mới kích hoạt cooldown = `max(GEMINI_QUOTA_COOLDOWN_SECONDS, RetryInfo, Retry-After, thời gian tới nửa đêm America/Los_Angeles nếu là quota PerDay)`.
  - Nếu toàn bộ model trong vòng đều hết quota, ném `GeminiQuotaExhausted` → `/analyze` trả HTTP `503` kèm header `Retry-After`.
  - Nếu bước `assess` đổi model, kết quả `extract_claims` trước đó vẫn được giữ nguyên.

### 3.6. Cache kết quả & Số liệu SQLite (`metrics.db`)

- **Bảng `analysis_metrics` & `feedback` (`metrics.py`):**
  - Mỗi lượt đi qua `/analyze` (sau kiểm tra hạn mức IP/key/global) đều ghi 1 dòng theo `request_id` (UUID v4), kể cả cache hit, timeout hay `503`.
  - Lưu `content_hash` (SHA-256 của text chuẩn hóa NFKC + gộp khoảng trắng), `text_length`, `platform`, `http_status`, `verdict`, `confidence`, thời gian từng bước (`extract_ms`, `evidence_ms`, `assess_ms`, `total_ms`), model, số lượt gọi/credit provider, `gemini_usage` JSON, `cache_hit`, và `estimated_cost_usd` (tính từ `GEMINI_TOKEN_PRICES` và `TAVILY_USD_PER_CREDIT` nếu được cấu hình). Nếu ghi `analysis_metrics` thất bại khi response đang là `200`, API trả `503`.
  - `GET /api/v1/stats/summary` tính trực tiếp từ SQLite: tỷ lệ verdict chia theo số lượt có verdict (`verdict IS NOT NULL`), p95 lấy phần tử thứ `ceil(0.95 × n)` trên toàn bộ lượt đã ghi, chi phí trung bình chia theo số lượt tính được giá, `helpful_rate` chia theo `feedback_count`.
- **Bảng `analysis_cache` (`analysis_cache.py`):**
  - Khóa chính gồm: `(content_hash [lowercase + gộp khoảng trắng], prompt_version [SHA-256 của EXTRACT_CLAIMS_PROMPT + ASSESS_PROMPT], model_id, lang_hash)`.
  - Hit cache miễn `RATE_LIMIT_PER_DAY_KEY` và bỏ qua orchestrator, nhưng vẫn tính IP limit, global limit và ghi dòng `cache_hit=1` với UUID mới và chi phí `0.0`.
  - TTL mặc định: `86400s` (24h) nếu `confidence_score ≥ 0.8` (trừ `unverified`), `3600s` (1h) nếu `< 0.8`, `900s` (15 phút) nếu `unverified`. Đặt TTL `= 0` để tắt ghi nhóm đó.
  - Không lưu cache nếu bị timeout, có provider `"error"`, hoặc response chứa lại `text` hay `page_url` (kể cả dạng URL-encoded hoặc HTML-escaped). `bypass_cache=true` bỏ qua cả đọc lẫn ghi.

---

## 4. Hệ thống Benchmark (`scripts/benchmark/`)

- Script `scripts/benchmark/run_benchmark.py` so sánh **3 chế độ** trên cùng bộ dataset CSV (`dataset_vn_benchmark_100.csv`, `dataset.csv`, ...):
  1. `llm_only`: Gemini đánh giá trực tiếp từ kiến thức nội tại (`LLM_ONLY_PROMPT`, không công cụ tìm kiếm).
  2. `llm_factcheck`: Dùng `AnalysisOrchestrator` nhưng tắt Tavily (chỉ Gemini + Google Fact Check).
  3. `full`: Pipeline đầy đủ (Gemini + Google Fact Check + Tavily).
- Hỗ trợ giới hạn RPM/retry khi gặp 429, cache resume tại `scripts/benchmark/.cache/results_v2.db`, và xuất thư mục kết quả theo giờ Việt Nam gồm `report.md` (Macro-F1 kèm 95% Bootstrap CI, Accuracy, kiểm định McNemar, chi phí, p50/p95, ma trận nhầm lẫn), `raw.csv`, `chart.png` và `summary.json`.

---

## 5. Giới hạn kỹ thuật đã biết & Hướng mở rộng

- **Giới hạn hiện tại:**
  - Bộ đếm rate limit và cooldown Gemini nằm trong RAM từng process (mất khi restart, không chia sẻ giữa nhiều worker).
  - SQLite dùng chung 1 file local cho metrics, feedback và cache; chưa có bảng lịch sử phân tích cho người dùng cuối.
  - Extension mới cài đặt adapter và quyền host cho Facebook và Reddit (schema backend đã chấp nhận thêm `"x"`).
  - Giao diện feedback 5 sao của extension và backend `/api/v1/feedback` (`helpful`, `reason`) đang lệch schema nên extension tạm tắt gửi mạng (`FEEDBACK_ENDPOINT_ENABLED = false`).
  - `trusted_domains.json` hiện chỉ có 4 domain quốc tế (`reuters.com`, `who.int`, `factcheck.org`, `britannica.com`), chưa đưa các báo Việt Nam vào tier xếp hạng ở backend (dù `publisher-names.json` ở extension đã có sẵn tên hiển thị).
  - Xác thực giữa extension và backend đang dùng `VITE_EXTENSION_API_KEY` tĩnh đóng gói trong bundle (chi tiết rủi ro xem [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)).
- **Điểm mở rộng đã thiết kế sẵn:**
  - **Thêm nền tảng (ví dụ X):** Tạo adapter implement `PlatformAdapter`, đăng ký ở `adapters/index.ts`, cập nhật `matches`/`host_permissions` trong `extension/vite.config.ts`.
  - **Thêm nguồn bằng chứng:** Tạo lớp kế thừa `BaseService` trong `backend/app/services/` và nạp vào `AnalysisOrchestrator`.
  - **Scale nhiều worker:** Tách rate limiter, model cooldown và cache sang Redis hoặc cơ sở dữ liệu dùng chung ở lớp API.
