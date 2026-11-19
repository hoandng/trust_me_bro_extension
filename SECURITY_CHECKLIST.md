# SECURITY_CHECKLIST

Tài liệu kiểm kê mối đe doạ, biện pháp bảo mật đang có trong mã nguồn, luồng dữ liệu, rủi ro còn lại và quy trình xử lý khi lộ khoá của TrustMeBro.

Cập nhật: 19/11/2026.

## Kiểm soát bảo mật

| Mối đe doạ                                       | Biện pháp                                                                                                    | File                                                                                                                               | Trạng thái |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| Lộ API key bên thứ ba ở client                   | Giữ `GEMINI_API_KEY`, `TAVILY_API_KEY`, `FACTCHECK_API_KEY` chỉ tại backend                                  | `backend/app/core/config.py`, `backend/app/services/`                                                                              | Có         |
| Gọi trái phép API backend                        | Xác thực `X-API-Key` và `X-Admin-API-Key` riêng biệt bằng `secrets.compare_digest`                           | `backend/app/api/deps.py`                                                                                                          | Có         |
| Lạm dụng chi phí API                             | Rate limit IP/phút (`10`), Key/24h (`100`), Global/ngày UTC (`1000`); trả `429` + `Retry-After`              | `backend/app/core/rate_limit.py`, `backend/app/api/deps.py`                                                                        | Có         |
| Giả mạo IP qua `X-Forwarded-For`                 | Mặc định `TRUST_PROXY_HEADERS=false`; chỉ đọc header khi peer thuộc `TRUSTED_PROXY_NETWORKS`                 | `backend/app/api/deps.py`                                                                                                          | Có         |
| Request payload quá lớn                          | Chặn `Content-Length > MAX_BODY_SIZE_BYTES` (`8192`) với mã `413`                                            | `backend/app/main.py`                                                                                                              | Có         |
| Lộ stacktrace, schema hoặc clickjacking          | Tắt `/docs`, `/redoc`, `/openapi.json` khi `ENV=production`; gắn 4 security headers; trả `500` chung         | `backend/app/main.py`                                                                                                              | Có         |
| Prompt injection và ảo giác URL/ký hiệu          | Bọc `<post>...</post>`, trung hòa `[[`/`]]`, Structured Output, lọc URL ngoài bằng chứng, làm sạch marker    | `backend/app/prompts/gemini_prompts.py`, `backend/app/services/gemini_service.py`                                                  | Có         |
| Lộ bí mật hoặc bài đăng qua log/cache            | `JSONFormatter` che key/token; `httpx` mức `WARNING`; `_contains_request_content` chặn ghi cache lặp đầu vào | `backend/app/core/logging.py`, `backend/app/core/analysis_cache.py`                                                                | Có         |
| XSS và URL độc hại trên Extension                | Chỉ dùng `createElement`/`textContent`, closed Shadow DOM, lọc `http(s)` không credentials, CSP `'self'`     | `extension/src/features/analysis/sidepanel/render.ts`, `extension/src/features/analysis/source-url.ts`, `extension/vite.config.ts` | Có         |
| Content script giả mạo message nội bộ            | Ràng buộc `sender.url === chrome.runtime.getURL(SIDEPANEL_PATH)` cho thao tác trạng thái/feedback            | `extension/src/entrypoints/background.ts`                                                                                          | Có         |
| Rò rỉ nội dung gốc khi chia sẻ                   | `buildShareSummary` loại bỏ giải thích và URL nguồn nếu chứa lại văn bản hoặc `page_url` gốc                 | `extension/src/features/analysis/share-summary.ts`                                                                                 | Có         |
| Commit nhầm khóa hoặc DB vào Git                 | Quét `gitleaks` ở pre-commit và CI; chặn `.env` và `metrics.db` trong `.gitignore`                           | `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `.gitignore`                                                                | Có         |
| Trích xuất khóa tĩnh từ bundle Extension         | Xác thực theo người dùng (OAuth/JWT) thay cho `VITE_EXTENSION_API_KEY`                                       | —                                                                                                                                  | Chưa có    |
| Request `Transfer-Encoding: chunked` vượt ngưỡng | Giới hạn kích thước body theo luồng đọc thực tế khi thiếu `Content-Length`                                   | —                                                                                                                                  | Chưa có    |
| Chạy nhiều worker không đồng bộ hạn mức          | Lưu bộ đếm rate limit và cooldown trên kho chia sẻ (như Redis)                                               | —                                                                                                                                  | Chưa có    |

## Dữ liệu gửi tới bên thứ ba và dữ liệu được lưu

| Điểm đến / Nơi lưu               | Dữ liệu truyền hoặc lưu                                                                                                                                                                                                                                                                            |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Google Gemini API                | Văn bản đã trung hòa `[[`/`]]`, `claim` và bằng chứng thu được; mọi lệnh gọi truyền `store=False`                                                                                                                                                                                                  |
| Google Fact Check Tools API      | Truy vấn ngắn trích từ `main_claim` (tối đa 2 truy vấn) và `languageCode`                                                                                                                                                                                                                          |
| Tavily Search API                | Truy vấn ngắn trích từ `main_claim` (tối đa 2 truy vấn) và danh sách domain lọc nếu cấu hình                                                                                                                                                                                                       |
| SQLite `backend/data/metrics.db` | Bảng `analysis_metrics` lưu `content_hash` (SHA-256 NFKC), độ dài văn bản, `platform`, độ trễ, verdict, chi phí (không lưu văn bản gốc/`page_url`). Bảng `feedback` lưu `request_id`, `helpful`, `reason`. Bảng `analysis_cache` lưu `AnalyzeResponse` đã loại phản hồi chứa lại `text`/`page_url` |
| Trình duyệt (Extension)          | RAM Service Worker (`tabRuns`) giữ state đầy đủ và xóa khi đóng/chuyển tab; `chrome.storage.session` chỉ lưu `{status, request_id?}` và `geminiModelCatalog`; `chrome.storage.local` chỉ lưu `preferredGeminiModel`                                                                                |

## Rủi ro còn lại

- `VITE_EXTENSION_API_KEY` nằm trong bundle `extension/dist/`; người dùng có thể giải nén để trích khóa và gọi trực tiếp backend.
- `RateLimiter` và `GeminiModelPool` lưu trên RAM từng process, mất trạng thái khi khởi động lại và không đồng bộ khi chạy nhiều worker.
- `security_middleware` chỉ kiểm tra header `Content-Length`: request `chunked` không bị chặn ở middleware, còn giá trị `Content-Length` không phải số nguyên gây lỗi `500`.
- Phòng vệ prompt injection mang tính giảm thiểu xác suất, không loại trừ hoàn toàn tác động của nội dung độc hại lên mô hình ngôn ngữ.
- Schema feedback giữa UI Extension (`rating`, `comment`) và backend (`helpful`, `reason`) đang lệch nhau; extension tạm chặn gửi mạng qua `FEEDBACK_ENDPOINT_ENABLED = false`.

## Khi lộ khoá

1. Thu hồi ngay khoá bị lộ tại nhà cung cấp tương ứng (Google AI Studio cho `GEMINI_API_KEY`, Tavily Dashboard cho `TAVILY_API_KEY`, Google Cloud Console cho `FACTCHECK_API_KEY`) hoặc sinh khoá ngẫu nhiên mới cho `EXTENSION_API_KEY` / `ADMIN_API_KEY`.
2. Cập nhật khoá mới vào `backend/.env` (và `extension/.env` rồi build lại `extension/dist/` nếu đổi `EXTENSION_API_KEY`), sau đó khởi động lại backend.
3. Kiểm tra nhật ký sử dụng và hạn mức chi phí trên trang quản trị của nhà cung cấp để phát hiện lưu lượng bất thường.
4. Nếu khoá đã bị đẩy lên Git, chạy `gitleaks` rà toàn bộ lịch sử, làm sạch commit chứa bí mật (ví dụ `git filter-repo`) và thông báo các thành viên kéo lại lịch sử mới.

Chi tiết kiến trúc xác thực và lưu trữ xem [ARCHITECTURE.md](ARCHITECTURE.md).
