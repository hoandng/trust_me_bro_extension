# ARCHITECTURE.md

> Dự án: **Trình mở rộng (browser extension) kiểm tra độ tin cậy bài đăng mạng xã hội**
> Phạm vi hiện tại gồm extension cho Facebook và Reddit, bộ chọn model Gemini và cơ chế chuyển model theo quota.

## 1. Kiến trúc tổng quan

Mô hình: **Client-Server**, trong đó Client là Chrome Extension (Manifest V3), Server là REST API backend độc lập đóng vai trò "orchestrator" gọi nhiều dịch vụ AI/fact-check bên ngoài rồi tổng hợp kết quả.

```text
[Facebook / Reddit]
        │ chọn văn bản hoặc bấm nút bài viết
        ▼
[Content script] ──chrome.runtime.sendMessage──► [Background service worker]
                                                        │ HTTP
                                                        ▼
                                                   [FastAPI]
                                                        │
                                                [Orchestrator]
                                                        │
                                         [Gemini / Fact Check / Tavily]
                                                        │ kết quả
                                                        ▼
[Side panel] ◄──theo dõi chrome.storage.session── [Background service worker]
```

**Vì sao chọn kiến trúc này:**
- Tách biệt extension (chỉ làm UI + bắt sự kiện) khỏi backend (chứa toàn bộ logic AI, API key) → **bảo mật**: API key của Gemini/Tavily/Fact Check không bao giờ nằm trong code extension (client-side), tránh bị lộ khi người dùng inspect extension.
- Backend đóng vai trò orchestrator, dễ thêm/bớt/nâng cấp nguồn dữ liệu (thêm API mới) mà không cần cập nhật extension.
- Dễ mở rộng sang nền tảng khác như X vì logic phân tích nằm ở backend và mỗi nền tảng có adapter riêng.

## 2. Các thành phần chính

### 2.1. Browser Extension (Client)

- **Kiến trúc tổ chức file:** Feature-based modular architecture, tách điểm chạy của Manifest V3 khỏi module tính năng và hạ tầng.
- **Công nghệ:** TypeScript strict, HTML/CSS và DOM thuần, Vite. Manifest được tạo bằng plugin nội bộ trong `extension/vite.config.ts`.
- **Nền tảng hiện có:** Facebook và Reddit. Reddit có thêm nút kiểm chứng trong trang chi tiết bài viết.

```text
extension/
├── src/
│   ├── entrypoints/
│   │   ├── background.ts           # đăng ký message listener
│   │   ├── content.ts              # khởi tạo tương tác trên trang
│   │   └── sidepanel/              # HTML và khởi tạo side panel
│   ├── features/
│   │   └── analysis/
│   │       ├── types.ts            # request, response backend/UI, trạng thái
│   │       ├── state-store.ts      # khóa và trạng thái phân tích theo tab
│   │       ├── model-preference.ts # model ưu tiên trong chrome.storage.local
│   │       ├── background/
│   │       │   ├── handle-analysis.ts # điều phối loading → API → success/error
│   │       │   ├── analysis-api.ts    # endpoint phân tích
│   │       │   └── map-response.ts    # chuyển response backend thành dữ liệu UI
│   │       ├── content/
│   │       │   ├── selection-controller.ts
│   │       │   ├── adapters/       # interface, registry, Facebook, Reddit
│   │       │   └── ui/             # nút nổi trong Shadow DOM
│   │       └── sidepanel/
│   │           ├── controller.ts  # sự kiện tab, subscription, retry, chọn model
│   │           ├── render.ts      # DOM, loading, kết quả, sao chép
│   │           └── index.css
│   ├── infrastructure/
│   │   ├── api/backend-client.ts   # HTTP, header, timeout, lỗi mạng
│   │   └── storage/session-store.ts # adapter chrome.storage.session
│   └── shared/
│       ├── messages.ts            # hợp đồng và kiểm tra message đầu vào
│       └── config.ts              # đường dẫn side panel dùng chung với Vite
├── tests/                         # kiểm tra module với API/Chrome mock
├── public/icons/
└── vite.config.ts
```

**Quy tắc phụ thuộc:**

- `entrypoints/` chỉ đăng ký listener và khởi tạo tính năng.
- `features/<tên>/` giữ logic, dữ liệu và giao diện của tính năng đó. Module background không import DOM của content script/side panel; content script không import HTTP client hoặc logic background.
- Module dùng ở cả background và side panel đặt ở gốc tính năng, như `state-store.ts` và `model-preference.ts`.
- `infrastructure/` bao bọc HTTP và Chrome Storage; không import logic từ `features/` hoặc `entrypoints/`.
- `shared/` chứa hợp đồng giao tiếp và cấu hình dùng chung. `shared/messages.ts` chỉ import **type** của tính năng, không kéo mã thực thi của tính năng sang ngữ cảnh khác.
- Mọi import kiểu dữ liệu dùng `import type` để tránh đưa mã không cần thiết vào bundle.

**Luồng phân tích hiện tại:**

1. `entrypoints/content.ts` khởi tạo `initSelectionController()`, chọn adapter theo URL (`RedditAdapter` hoặc `FacebookAdapter`) và gọi `adapter.init()` nếu có.
   - Trên cả Facebook và Reddit: khi bôi đen văn bản dài 20–2000 ký tự (debounce 150ms), `FloatingButton` (trong closed Shadow DOM) hiện phía trên vùng chọn.
   - Riêng trên Reddit: tại trang chi tiết bài viết (`/comments/`), `RedditAdapter` dùng `IntersectionObserver` và `MutationObserver` để quét thẻ `<shreddit-post>`, bóc tách tiêu đề (`[slot="title"]`/`post-title`), nội dung (`[slot="text-body"]` hoặc `#-post-rtjson-content` trong shadowRoot) và link bài báo (`content-href`), sau đó gắn viền nhận diện và chèn nút **"Kiểm chứng bài viết"**.
2. Nút nổi hoặc nút bài viết Reddit gửi `ANALYZE_REQUEST` qua `chrome.runtime.sendMessage`.
3. `entrypoints/background.ts` kiểm tra hợp đồng message bằng `isAnalyzeRequest()` rồi chuyển cho `handle-analysis.ts`.
4. Handler mở side panel ngay trong ngữ cảnh user gesture (`chrome.sidePanel.open({ tabId })`; nếu bị chặn sẽ đặt badge `!` màu đỏ trên icon tiện ích), đọc model ưu tiên `preferredGeminiModel` từ `chrome.storage.local` cho lượt này, ghi trạng thái `loading` vào `chrome.storage.session` và gọi `analysis-api.ts`. HTTP client gửi `POST /api/v1/analyze` kèm `X-API-Key`, `model_id` (nếu có) và timeout 60 giây.
5. `map-response.ts` chuyển `verdict` (`likely_true` → `Thật`, `likely_false` → `Giả`, `mixed` → `Thiếu ngữ cảnh`, `unverified` → `Không thể kiểm chứng`), quy đổi `confidence_score` sang phần trăm (`0–100`), tổng hợp `service_status` và giữ `request_id` cùng `model_usage`. Handler ghi trạng thái `success` hoặc `error`.
6. Side panel theo dõi `tabState_<tabId>` trong `chrome.storage.session` và dùng `GET_ANALYSIS_STATE` để đọc nội dung hiển thị từ bộ nhớ của service worker. Khi khởi tạo, panel gọi `GET /api/v1/models` để điền bộ chọn model. Nút **Thử lại** gửi `RETRY_ANALYSIS` cho tab đang mở để dùng lại payload còn trong RAM và đọc lựa chọn model mới nhất.

`chrome.storage.session` chỉ giữ trạng thái và UUID theo tab. Request gốc và kết quả chi tiết có thể trích nguyên văn bài đăng nên chỉ nằm trong RAM của worker. Dữ liệu chi tiết mất khi tab đóng, điều hướng hoặc worker khởi động lại. Khi đó người dùng có thể chọn lại bài đăng để phân tích.

**Mở rộng:**

- Thêm mạng xã hội: tạo adapter implement `PlatformAdapter` trong `features/analysis/content/adapters/`, đăng ký trong `index.ts` và cập nhật matches/host permissions ở Vite.
- Thêm tóm tắt bài báo: tạo `features/article-summary/` với `types.ts`, `content/`, `background/`, `sidepanel/`; thêm hợp đồng message và nối tại các entrypoint. Xử lý AI vẫn nằm ở backend.
- Thêm cache: tạo adapter `infrastructure/cache/` khi triển khai, để từng tính năng tự quyết định khóa, TTL và điều kiện bỏ qua cache. Tách cache kết quả khỏi trạng thái UI theo tab.
- Thêm service AI/search bên ngoài: triển khai ở backend; extension chỉ thêm API client hoặc mapper của tính năng khi hợp đồng backend thay đổi.

Chi tiết phát triển, debug và kiểm tra thủ công: [`extension/README.md`](extension/README.md).

### 2.2. Backend API (Server)
- **Framework:** Python + FastAPI
- **Kiến trúc API:** `GET /health` kiểm tra tiến trình. `GET /api/v1/models`, `POST /api/v1/analyze` và `POST /api/v1/feedback` yêu cầu `X-API-Key`. Hai endpoint POST dùng chung rate limit. `GET /api/v1/stats/summary` yêu cầu `X-Admin-API-Key` riêng.
- **Cấu trúc thư mục thực tế:**
  ```
  backend/
  ├── app/
  │   ├── main.py                 # entrypoint FastAPI
  │   ├── api/
  │   │   ├── deps.py             # Dependency injection (orchestrator, rate limiter)
  │   │   └── v1/
  │   │       └── analyze.py      # route /analyze và /models
  │   ├── core/
  │   │   ├── config.py           # đọc env, settings
  │   │   ├── rate_limit.py       # rate limiter (chống spam)
  │   │   └── logging.py          # cấu hình logger
  │   ├── prompts/
  │   │   └── gemini_prompts.py   # Các mẫu prompt chi tiết cho Gemini
  │   ├── services/               # MODULE HOÁ theo từng nguồn dữ liệu
  │   │   ├── factcheck_service.py# gọi Google Fact Check Tools API
  │   │   ├── gemini_service.py   # gọi Interactions API để trích xuất và đánh giá
  │   │   ├── gemini_model_pool.py # cooldown theo model, dùng chung trong process
  │   │   ├── tavily_service.py   # gọi Tavily API (tìm kiếm nguồn tham khảo)
  │   │   └── base_service.py     # interface chung
  │   ├── orchestrator/
  │   │   └── analysis_orchestrator.py  # gọi logic các service, tổng hợp kết quả
  │   └── schemas/
  │       ├── internal.py         # context / schemas dùng nội bộ
  │       ├── request.py          # AnalyzeRequest (text, url, platform...)
  │       └── response.py         # AnalyzeResponse (verdict, score, sources[], explanation)
  ├── tests/                      # Unit/Integration tests
  ├── .env.example
  └── requirements.txt
  ```

- **Vì sao module hoá theo `services/` + `orchestrator/`:**
  - Fact Check và Tavily dùng chung `BaseService.check(ctx)` để tra cứu. `GeminiService` có hai phương thức riêng là `extract_claims` và `assess`.
  - FastAPI lifespan tạo orchestrator và các service một lần mỗi worker. Fact Check và Tavily dùng chung một `httpx.AsyncClient`. Gemini dùng chung SDK client. `get_orchestrator()` lấy orchestrator từ `app.state` và lifespan đóng client khi shutdown. Mỗi lượt phân tích truyền riêng lựa chọn model và `model_usage`.

### 2.3. Luồng xử lý tại Orchestrator

Pipeline có một deadline chung theo đồng hồ monotonic, mặc định 25 giây qua `ANALYSIS_TIMEOUT_SECONDS`. Giới hạn của từng bước được cắt theo thời gian còn lại. Khi hết ngân sách, orchestrator hủy tác vụ còn chờ và trả `unverified` kèm nguồn đã về nếu có. Log JSON ghi `extract_ms`, `evidence_ms`, `assess_ms`, `total_ms` và `timeout_stage`. Thời gian của bước chưa chạy là `null`.

1. **Giai đoạn 0 (Trích xuất & Lọc):**
   - `gemini_service.extract_claims` tìm khẳng định chính (`main_claim`), ngôn ngữ (`detected_lang`), tối đa 3 truy vấn tìm kiếm (`search_queries`) và cờ `is_checkable`. Bước này có timeout 20 giây ở orchestrator (15 giây mỗi lượt gọi SDK, tối đa 2 lần thử).
   - Nếu trích xuất lỗi hoặc rỗng → trả ngay `unverified` (`confidence_score=0.0`, `service_status.gemini="error"`).
   - Nếu `is_checkable=false` (không có yếu tố kiểm chứng được như ý kiến cá nhân, câu hỏi, quảng cáo) → trả ngay verdict `unverified` (`confidence_score=0.0`) kèm giải thích, không gọi tiếp API để tiết kiệm chi phí.
2. **Giai đoạn 1 (Thu thập bằng chứng):**
   - Lấy các truy vấn đầu theo `SEARCH_QUERY_LIMIT` (mặc định 2, cho phép 1–2), bỏ chuỗi rỗng và trùng. Nếu không còn truy vấn, dùng `main_claim` khi có. Mỗi cặp truy vấn và provider chạy song song với timeout 10 giây, cả nhóm có timeout 15 giây. Tối đa 4 lượt gọi service và 8 request HTTP tìm kiếm, tính cả fallback.
     - `factcheck_service` truy vấn `claims:search` (`pageSize=10`) với `languageCode=ctx.lang`. Nếu kết quả rỗng và có `ctx.lang`, service thử lại một lần không giới hạn ngôn ngữ. Service chuẩn hóa `textualRating` rồi tra toàn bộ nhãn trong bảng rating tiếng Anh và tiếng Việt. Ví dụ, `Not true` và `sai sự thật` cho `refutes`, `Mostly True` cho `supports`, còn `Half True`, `thiếu ngữ cảnh` và nhãn chưa nhận diện cho `neutral`. Mỗi nguồn Fact Check giữ kết quả tra cứu trong `original_stance` và lấy `claim_text` từ `text` của claim mà Google trả về.
     - `tavily_service` tìm `topic="news"` trước và thử `topic="general"` một lần nếu không có nguồn. Cả hai lượt dùng `search_depth="basic"`, `max_results=5` và các bộ lọc domain hiện có. Service giữ `published_date` khi Tavily cung cấp và trích xuất tên miền làm `publisher`.
3. **Giai đoạn 2 (Đánh giá tổng hợp):**
   - Orchestrator gộp kết quả theo thứ tự truy vấn, giữ bản Fact Check khi trùng URL với Tavily. Sau đó xếp nguồn theo `tier1`, `tier2`, `default` và lấy tối đa 8 nguồn. Thứ tự gộp được giữ trong cùng tier. Các nhóm domain nằm trong `backend/app/core/trusted_domains.json` và được nạp khi khởi động. Domain con được so khớp theo ranh giới hostname. Domain ngoài danh sách thuộc `default`. Nếu không có nguồn nào, trả `unverified` với `confidence_score=0.3`.
   - `gemini_service.assess` đánh giá các nguồn thu được (timeout 20 giây, tối đa 2 lần thử). Gemini dùng structured output (JSON schema) ở cả hai bước. Backend kiểm tra kết quả bằng Pydantic và lọc bỏ URL trong `source_stances` nếu URL đó không nằm trong tập bằng chứng. Với mỗi nguồn Fact Check, prompt yêu cầu Gemini trả `factcheck_match=true` khi `claim_text` và khẳng định trích xuất từ bài đăng diễn đạt cùng một mệnh đề. Nếu thiếu cờ này, backend mặc định `false`. `factcheck_match` là trường nội bộ của bước đánh giá.
   - Prompt nhận ngày hiện tại theo giờ Việt Nam, tier và ngày xuất bản của từng nguồn nếu có. Gemini cần chỉ ra bằng chứng có trước sự kiện hoặc dấu hiệu tin cũ được chia sẻ như tin mới, và nêu rõ khi dữ liệu ngày chưa đủ để kết luận.
   - Orchestrator áp dụng các quy tắc hậu xử lý:
     - Chỉ cập nhật `stance` của nguồn Tavily theo kết quả Gemini. Nguồn Fact Check giữ stance từ rating, kể cả khi trùng URL với nguồn Tavily.
     - **Ưu tiên Fact Check.** Orchestrator chỉ xét nguồn Fact Check đầu tiên trong thứ tự gộp, với điều kiện nguồn đó đã được gửi cho Gemini, bước đánh giá thành công, `claim_text` không rỗng và `factcheck_match=true` cho đúng URL. Nếu `original_stance` là `supports` hoặc `refutes`, verdict ưu tiên tương ứng là `likely_true` hoặc `likely_false`. Khi verdict thực sự thay đổi, nâng `confidence_score` lên ít nhất `0.8`.
     - **Ràng buộc nhất quán:** Nếu `verdict` là `"likely_true"` hoặc `"likely_false"` mà `confidence_score < 0.5` thì nâng lên `0.5`; nếu `verdict == "unverified"` thì giới hạn `confidence_score = min(confidence_score, 0.4)`.
     - **Xử lý lỗi linh hoạt.** Một lượt tra cứu lỗi hoặc timeout được phản ánh qua `service_status` của provider tương ứng. Các lượt thành công vẫn đóng góp nguồn cho bước đánh giá.
4. Trả về `request_id` (UUID v4), `verdict`, `confidence_score`, `explanation`, `sources`, `service_status` và `model_usage`. Ví dụ khi model ưu tiên chạm quota ở bước đánh giá:
   ```json
   {
     "request_id": "88a7b1c8-fb0b-44a8-9f07-02008a8ad22f",
     "verdict": "likely_true",
     "confidence_score": 0.8,
     "explanation": "Nguồn tham khảo ủng hộ khẳng định.",
     "sources": [
       {
         "title": "Bài kiểm chứng",
         "url": "https://example.com/fact-check",
         "publisher": "Example",
         "snippet": "True",
         "stance": "supports",
         "original_stance": "supports",
         "claim_text": "Khẳng định được bài kiểm chứng đánh giá.",
         "published_date": null
       }
     ],
     "service_status": {
       "factcheck": "ok",
       "tavily": "empty",
       "gemini": "ok"
     },
     "model_usage": {
       "requested_model": "gemini-3.1-flash-lite",
       "extraction_model": "gemini-3.1-flash-lite",
       "assessment_model": "gemini-3.5-flash",
       "fallbacks": [{"stage": "assessment", "model": "gemini-3.1-flash-lite", "reason": "quota"}]
     }
   }
   ```

### 2.4. Chọn model Gemini và xử lý quota

`GEMINI_MODEL` xác định model mặc định và `GEMINI_MODELS` bổ sung các model theo thứ tự. `GET /api/v1/models` trả danh sách đã loại tên trùng. `POST /api/v1/analyze` dùng `model_id` nếu được cung cấp và trả `422` nếu model đó nằm ngoài danh sách.

Mỗi bước Gemini bắt đầu từ model ưu tiên, thử theo vòng và bỏ qua model đang cooldown. HTTP `429` từ Gemini kích hoạt cooldown dùng chung theo model trong process. Nếu cả danh sách hết quota, endpoint phân tích trả `503` cùng `Retry-After`. Nếu bước đánh giá chuyển model, kết quả trích xuất đã có vẫn được sử dụng. Xem chi tiết biến môi trường và cách tính cooldown trong [hướng dẫn backend](backend/README.md#chọn-model-và-chuyển-model-khi-hết-quota).

### 2.5. Số liệu phân tích và phản hồi

Lifespan khởi tạo `backend/data/metrics.db` bằng `sqlite3`. Backend ghi một dòng theo UUID cho mỗi lượt vào pipeline, kể cả lượt degraded hoặc lỗi. Dòng ghi gồm thời điểm UTC, platform, độ dài văn bản, SHA-256 sau NFKC và gộp khoảng trắng, trạng thái HTTP, verdict, confidence, thời gian pipeline, model, số request đã thử gửi theo provider, usage trả về, `cache_hit` và chi phí USD ước tính. Lượt chưa có verdict dùng `null`. Gemini Interactions dùng `store=false`. Chỉ metadata đã chọn được chuyển đến SQLite và log.

`POST /api/v1/feedback` cập nhật một phản hồi cho mỗi UUID đã có verdict. `GET /api/v1/stats/summary` tổng hợp trực tiếp từ SQLite. Tỷ lệ verdict chia theo số lượt có verdict. Độ trễ trung bình và p95 tính trên mọi lượt đã ghi. p95 lấy giá trị tại vị trí `ceil(0.95 × n)` sau khi sắp xếp. Chi phí trung bình chia theo số lượt ước tính được và tỷ lệ helpful chia theo số lượt đã phản hồi.

### 2.6. Benchmark theo dataset

`scripts/benchmark/` chạy bốn chế độ `llm_only`, `factcheck_only`, `llm_factcheck` và `full` trên cùng dataset CSV. Hai chế độ có Gemini và nguồn dùng lại orchestrator. `llm_factcheck` bỏ qua Tavily. Runner dùng bộ đo chi phí B1, cache kết quả theo mẫu–chế độ trong SQLite riêng và xuất báo cáo cùng phiếu chấm citation. Xem [hướng dẫn benchmark](scripts/benchmark/README.md).

## 3. Bảo mật (quan trọng — đọc kỹ trước khi code)

| Vấn đề | Giải pháp |
|---|---|
| API key (Gemini, Tavily, Fact Check) | Chỉ cấu hình ở backend qua biến môi trường hoặc `backend/.env`. |
| Giao tiếp Extension ↔ Backend | Local dùng HTTP trên loopback. Khi triển khai, cấu hình HTTPS ở tầng phục vụ backend. Extension gửi key riêng qua `X-API-Key`. |
| Rate limiting | Backend đếm lượt phân tích theo IP, theo key và theo tổng lượt trong process. IP đến từ kết nối trực tiếp hoặc từ chuỗi `X-Forwarded-For` đã kiểm tra khi bật chế độ proxy tin cậy. |
| Dữ liệu người dùng | Backend xử lý nội dung theo request và lưu metadata số liệu vào SQLite. Extension giữ nội dung và kết quả chi tiết trong RAM, còn Chrome storage giữ trạng thái và UUID. Xem [checklist bảo mật](SECURITY_CHECKLIST.md). |
| CORS | Backend bật CORS khi có `ALLOWED_ORIGINS`. Mỗi origin của extension có dạng `chrome-extension://<extension-id>`. |
| Input validation | Backend kiểm tra độ dài văn bản và giới hạn `Content-Length`. Prompt Gemini đặt văn bản trong thẻ `<post>` và kiểm tra JSON đầu ra. |

Key tĩnh `VITE_EXTENSION_API_KEY` được nhúng vào bundle khi build và có thể đọc được từ extension. Xác thực bằng token cấp động nằm trong [roadmap phát hành](ROADMAP.md).

## 4. Các API bên ngoài sử dụng (bản demo)

| API | Mục đích | Ghi chú |
|---|---|---|
| Google Fact Check Tools API | Tìm claim đã được các tổ chức fact-check xác minh trước đó | Miễn phí, có giới hạn quota |
| Gemini API | Phân tích ngữ nghĩa, tóm tắt, tổng hợp đánh giá cuối, sinh giải thích | Cần API key, tính phí theo token |
| Tavily API | Search engine tối ưu cho AI, tìm nguồn tin liên quan real-time | Cần API key, có free tier |

## 5. Giới hạn/nợ kỹ thuật đã biết (bản demo)
- SQLite dùng cho số liệu và feedback. Cache kết quả và lịch sử phân tích chưa triển khai.
- Hỗ trợ Facebook và Reddit; DOM selector có thể hỏng khi nền tảng đổi giao diện → cần thiết kế adapter dễ sửa (mục 2.1).
- Static API key giữa extension–backend chưa đủ an toàn cho production.
- Bộ đếm lượt phân tích và cooldown Gemini nằm trong bộ nhớ của từng process và mất khi process khởi động lại.
- Google Fact Check Tools API có độ phủ dữ liệu tiếng Việt còn hạn chế, có thể thường xuyên trả về trạng thái rỗng ("empty") khi truy vấn nội dung tiếng Việt.

## 6. Định hướng mở rộng (đã tính trước trong kiến trúc)
- Thêm mạng xã hội mới → thêm adapter mới trong extension, không đổi backend.
- Thêm API/nguồn dữ liệu mới → thêm 1 service mới trong `services/`, đăng ký vào orchestrator.
- Chế độ tự động phân tích khi click vào post (thay vì bôi đen) → chỉ cần thêm 1 adapter method `injectButtonOnEachPost()`, luồng backend giữ nguyên.
- Khi cần lưu lịch sử/cache → thêm `database/` layer + Redis cache trước các service calls, không ảnh hưởng orchestrator logic.
