# SECURITY_CHECKLIST.md

> Tài liệu kiểm tra các biện pháp bảo mật và quyền riêng tư đã triển khai trong mã nguồn **Trust Me Bro**, các rủi ro còn tồn tại và phạm vi kiểm thử bảo mật hiện có.

---

## 1. Backend API (`backend/`)

### Xác thực & Phân quyền (`app/api/deps.py`)
- [x] **API key cho Extension (`X-API-Key`):** `POST /api/v1/analyze`, `POST /api/v1/feedback` và `GET /api/v1/models` yêu cầu header `X-API-Key`, so sánh bằng `secrets.compare_digest`. Trả `401` khi thiếu/sai key và `500` nếu server chưa cấu hình `EXTENSION_API_KEY`.
- [x] **API key cho Admin (`X-Admin-API-Key`):** `GET /api/v1/stats/summary` yêu cầu `X-Admin-API-Key` riêng biệt. Nếu `ADMIN_API_KEY` để trống hoặc trùng với `EXTENSION_API_KEY`, endpoint từ chối hoạt động với mã `503`.
- [x] **Tách biệt khóa dịch vụ bên thứ ba:** `GEMINI_API_KEY`, `TAVILY_API_KEY` và `FACTCHECK_API_KEY` chỉ đọc từ môi trường / `backend/.env` ở backend.

### Rate Limiting & Bảo vệ ngân sách (`app/core/rate_limit.py`, `app/api/deps.py`, `app/api/v1/analyze.py`)
- [x] **Giới hạn theo IP (`RATE_LIMIT_PER_MINUTE_IP`, mặc định `10`):** Áp dụng cho cả `POST /api/v1/analyze` (kể cả cache hit) và `POST /api/v1/feedback`.
- [x] **Giới hạn theo Key (`RATE_LIMIT_PER_DAY_KEY`, mặc định `100`):** Áp dụng trong cửa sổ 24 giờ cho `/feedback` và các lượt miss cache của `/analyze`. Lượt hit cache được miễn trừ giới hạn này.
- [x] **Ngưỡng trần toàn cục (`DAILY_ANALYZE_LIMIT_GLOBAL`, mặc định `1000`):** Kill switch đếm lượt theo ngày UTC trong từng process cho mọi lượt `/analyze` (kể cả cache hit) và `/feedback`. Vượt bất kỳ giới hạn nào trả `429` kèm header `Retry-After`.
- [x] **Phát hiện IP sau Reverse Proxy:** Mặc định `TRUST_PROXY_HEADERS=false` dùng IP kết nối trực tiếp (`request.client.host`). Khi bật `true`, backend chỉ đọc `X-Forwarded-For` nếu peer IP thuộc `TRUSTED_PROXY_NETWORKS`, duyệt từ phải sang trái để bỏ qua proxy tin cậy và lấy IP hợp lệ đầu tiên ngoài danh sách (chuẩn hóa IPv4-mapped IPv6, từ chối IP có `%` scope ID). Khi thiếu hoặc sai định dạng ở hop đang xét thì fallback về peer IP. Khuyến nghị chạy Uvicorn với `--no-proxy-headers` và chặn truy cập trực tiếp không đi qua proxy tin cậy.

### Kiểm tra đầu vào, HTTP Headers & Môi trường (`app/main.py`, `app/schemas/request.py`, `app/api/v1/metrics.py`)
- [x] **Giới hạn kích thước body (`MAX_BODY_SIZE_BYTES`, mặc định `8192`):** Middleware kiểm tra header `Content-Length` và trả `413` nếu vượt ngưỡng (lưu ý mục Rủi ro về request không có `Content-Length`).
- [x] **Validation schema nghiêm ngặt:**
  - `AnalyzeRequest`: `text` sau `strip()` phải dài `20–2000` ký tự; `platform` chỉ nhận `"facebook" | "x" | "reddit"`; `model_id` ngoài `settings.available_gemini_models` bị từ chối với `422`.
  - `FeedbackRequest`: cấu hình `extra="forbid"`, bắt buộc `request_id` chuẩn UUID v4, `helpful` kiểu `StrictBool`, `reason` thuộc tập `Literal` cố định.
- [x] **Security Response Headers:** Middleware gắn `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block` và `Strict-Transport-Security: max-age=31536000; includeSubDomains` cho mọi response đi qua `call_next`.
- [x] **Ẩn tài liệu API ở Production:** Đặt `ENV=production` sẽ tắt `/docs`, `/redoc` và `/openapi.json`.
- [x] **Xử lý ngoại lệ an toàn:** Global exception handler trả `{"detail": "Internal server error"}` với `exc_info=False`, không để lộ stacktrace hoặc payload ra HTTP response.

### Quyền riêng tư dữ liệu, Logging & Chống Prompt Injection (`app/core/`, `app/services/gemini_service.py`, `app/prompts/`)
- [x] **Không lưu/log nội dung bài đăng gốc:**
  - `analysis_metrics` chỉ lưu `text_length` và `content_hash` (SHA-256 sau chuẩn hóa NFKC + gộp khoảng trắng).
  - `JSONFormatter` che các chuỗi `api_key=...`, `Authorization: Bearer ...`, `X-API-Key: ...` và thay traceback mức `ERROR`/`CRITICAL` bằng `"Redacted stacktrace"`.
  - Mức log của `httpx` được đặt về `WARNING` để tránh ghi URL truy vấn Fact Check chứa claim.
  - Các nhánh lỗi Fact Check / Tavily / Gemini không đưa API key hoặc nội dung bài đăng vào thông báo lỗi/log.
  - File `backend/data/metrics.db` và `metrics.db-*` nằm trong `.gitignore`.
- [x] **Kiểm soát dữ liệu cache (`analysis_cache.py`):** Chỉ lưu cache khi không timeout, không có provider lỗi và `ttl > 0`. Hàm `_contains_request_content()` từ chối ghi cache nếu bất kỳ chuỗi nào trong response lặp lại `text` hoặc `page_url` (bao gồm cả dạng URL-decoded và HTML-unescaped).
- [x] **Chính sách API Gemini:** Mọi lời gọi `interactions.create` đều truyền `store=False`.
- [x] **Giảm thiểu Prompt Injection & XSS phía nguồn:**
  - Prompt đặt nội dung người dùng trong cặp thẻ `<post>...</post>` kèm chỉ thị bỏ qua mọi mệnh lệnh bên trong dữ liệu.
  - `neutralize_marker_delimiters()` vô hiệu hóa chuỗi `[[` và `]]` trong văn bản gốc, claim và dữ liệu nguồn trước khi gửi Gemini.
  - Kết quả đánh giá dùng Structured JSON Output (`Pydantic`), lọc bỏ mọi URL trong `source_stances` không nằm trong tập bằng chứng đã truyền, và chuẩn hóa ký hiệu đánh dấu giải thích qua `sanitize_explanation_markers()`.

---

## 2. Browser Extension (`extension/`)

- [x] **Quyền tối thiểu & CSP (`vite.config.ts`):** Manifest V3 chỉ khai báo quyền `sidePanel`, `storage` và `host_permissions` giới hạn cho `https://*.reddit.com/*`, `https://*.facebook.com/*` cùng `VITE_BACKEND_URL`. Đặt `content_security_policy.extension_pages` là `script-src 'self'; object-src 'self';`.
- [x] **Xác minh nguồn gửi message nội bộ (`background.ts`):** `GET_ANALYSIS_STATE`, `RETRY_ANALYSIS` và `SUBMIT_ANALYSIS_FEEDBACK` chỉ được xử lý khi `sender.url === chrome.runtime.getURL(SIDEPANEL_PATH)`, ngăn content script hoặc trang web giả mạo đọc/gửi trạng thái tab.
- [x] **Cách ly dữ liệu nhạy cảm trên trình duyệt:**
  - `chrome.storage.session` (`tabState_<tabId>`) chỉ lưu `{ status, request_id? }`; `chrome.storage.local` chỉ lưu `preferredGeminiModel`.
  - Văn bản gốc, `page_url` và kết quả phân tích chỉ giữ trong RAM của Service Worker (`tabRuns` Map) để hiển thị/thử lại và bị xóa ngay khi đóng tab hoặc chuyển trang (`tabs.onRemoved`, `tabs.onUpdated`).
- [x] **Chống XSS & URL độc hại khi render (`render.ts`, `explanation-parser.ts`, `source-url.ts`, `floating-button.ts`):**
  - Toàn bộ DOM Side Panel dựng bằng `document.createElement` và `.textContent` (không dùng `innerHTML`).
  - Nút nổi trên trang web cô lập trong `closed` Shadow DOM.
  - Link nguồn được kiểm tra qua `safeSourceUrl()` (chỉ nhận `http:`/`https:`, từ chối URL chứa `username`/`password` hoặc `javascript:`), mở tab mới với `rel="noopener noreferrer"`.
- [x] **Bảo vệ bản chia sẻ & cờ Feedback (`share-summary.ts`, `shared/config.ts`):**
  - `buildShareSummary()` loại bỏ ký hiệu đánh dấu và lọc bỏ giải thích hoặc URL nguồn nếu chứa lại văn bản hoặc `page_url` của bài gốc.
  - `FEEDBACK_ENDPOINT_ENABLED = false` chặn mọi yêu cầu gửi feedback từ extension qua mạng cho tới khi schema được đồng bộ với backend.

---

## 3. Rủi ro còn lại (Known Risks)

1. **Static API Key trong Extension (`VITE_EXTENSION_API_KEY`):** Khóa dùng chung được nhúng vào bundle extension khi build nên bất kỳ ai giải nén extension đều có thể trích xuất và dùng key này gửi request trực tiếp tới backend.
   - *Giảm thiểu hiện tại:* Rate limit theo IP/key/global và kích hoạt HTTPS ở tầng reverse proxy khi deploy.
   - *Hướng xử lý lâu dài:* Chuyển sang xác thực theo người dùng (OAuth / JWT / Firebase Auth) ở Milestone 5.
2. **Trạng thái Rate Limit & Cooldown nằm trong RAM từng process:** Nếu chạy nhiều Uvicorn worker hoặc nhiều instance, bộ đếm giới hạn và cooldown model Gemini không được chia sẻ và sẽ reset khi tiến trình khởi động lại.
3. **Kiểm tra `Content-Length` dựa trên header khai báo:** Middleware đọc `Content-Length`; request dùng `Transfer-Encoding: chunked` (không có header này) không bị chặn ở lớp middleware trước khi đọc body, còn giá trị `Content-Length` không phải số nguyên hợp lệ sẽ gây lỗi `500` qua global handler.
4. **Prompt Injection mang tính xác suất:** Các lớp `<post>`, trung hòa `[[`/`]]`, structured output và lọc URL giảm đáng kể rủi ro nhưng không đảm bảo tuyệt đối mô hình ngôn ngữ sẽ không bị ảnh hưởng bởi nội dung độc hại.
5. **Lệch schema Feedback giữa Client và Server:** UI Side Panel thiết kế đánh giá 5 sao + comment trong khi backend đang nhận `helpful` (boolean) + `reason`; hiện được cô lập an toàn nhờ `FEEDBACK_ENDPOINT_ENABLED = false`.

---

## 4. Kiểm thử bảo mật & Hồi quy hiện có

- **`backend/tests/test_security.py`:** `test_missing_api_key`, `test_rate_limit_ip`, `test_rate_limit_key`, `test_global_limit`, `test_body_too_large`, `test_proxy_rate_limit_uses_expected_ip`.
- **`backend/tests/test_api.py`:** Xác thực `X-API-Key` trên `/analyze` và `/models`, từ chối `model_id` ngoài danh sách (`422`), trả `503` + `Retry-After` khi hết quota.
- **`backend/tests/test_gemini_service.py`:** Bọc `<post>`, trung hòa `[[`/`]]` trong đầu vào và bằng chứng, làm sạch ký hiệu đánh dấu ở đầu ra, lọc URL ảo giác, không log nội dung nhạy cảm khi lỗi validation.
- **`backend/tests/test_metrics.py`:** Phân quyền admin `401`/`503`, validate `extra="forbid"` ở `/feedback`, chia sẻ rate limit với `/analyze`, kiểm chứng không có văn bản/`page_url` gốc trong SQLite hay log và mọi lời gọi Gemini dùng `store=False`.
- **`backend/tests/test_analysis_cache.py`:** Không cache khi timeout/lỗi/degraded hoặc khi response lặp lại `text`/`page_url` (kể cả URL-encoded), kiểm tra miễn `RATE_LIMIT_PER_DAY_KEY` nhưng vẫn tính IP & global limit khi hit cache.
- **`backend/tests/test_source_ranking.py`:** Kiểm tra ranh giới hostname chống giả mạo domain (`fakereuters.com`, `reuters.com@example.com`, URL lỗi).
- **`extension/tests/analysis.test.ts`:** Hợp đồng message & chặn sender ngoài Side Panel, chống XSS trong `renderExplanationSegments`, kiểm tra `safeSourceUrl`, đảm bảo `chrome.storage.session` chỉ chứa metadata, bảo vệ `buildShareSummary` và xác nhận `FEEDBACK_ENDPOINT_ENABLED = false` không gửi request mạng.
