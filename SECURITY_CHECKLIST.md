# SECURITY_CHECKLIST.md

## Backend
- ✅ Rate limiting theo IP và theo API key: Đã thêm `RateLimiter` (in-memory) và dependency `verify_api_key` để chặn request vượt mức. Cấu hình mặc định `10 req/min/IP`, `100 req/day/key`. Trả về `429 Too Many Requests` kèm theo header `Retry-After`.
  - *Lưu ý khi chạy nhiều instance (multiprocessing / K8s / load balancer)*: Vì RateLimiter đang ở dạng `in-memory` local variable, state đếm request này KHÔNG được share giữa các worker/instance. Do đó, nếu bạn có N instances đằng sau Load Balancer, một user có thể gửi tối đa `N * limit` requests. Nếu muốn limit chuẩn tuyệt đối khi scale, cần sử dụng shared-storage như `Redis` (ví dụ thư viện `slowapi` kết hợp redis-backend, hoặc viết tự ghi đè lên redis).
- ✅ Giới hạn kích thước body: Đã thêm middleware `security_middleware` chặn mọi request có `content-length` > 8KB. Trả về `413 Request Entity Too Large`.
- ✅ Security headers cơ bản: Đã cấu hình thêm các header: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Strict-Transport-Security` vào middleware.
- ✅ Ẩn Swagger/Redoc khi `ENV=production`: Các route `/docs` và `/openapi.json` sẽ bị vô hiệu hóa nếu set `env=production` ở config.
- ✅ Đảm bảo thông báo lỗi không lộ stacktrace: Đã chặn `Exception` chung ở cấp cao nhất `app.exception_handler`. Lỗi sẽ trả về json an toàn `{"detail": "Internal server error"}`. Stacktrace chỉ được ghi vào application log.
- ✅ Log an toàn: Cấu hình Redact thông tin nhạy cảm ở `app.core.logging`. Tự động ẩn các API Key bị log nhầm hoặc các Header như `Authorization` và `X-API-Key`. Text gửi lên từ người dùng cũng đã không được in thẳng ra (chỉ in chiều dài văn bản).
- ✅ Thêm cơ chế "kill switch" và ngân sách: Sử dụng biến `DAILY_ANALYZE_LIMIT_GLOBAL` qua RateLimiter để chặn khi tổng số lượt call API/ngày trên toàn hệ thống vượt ngưỡng (bảo vệ hóa đơn Gemini/Tavily).

## Extension
- ✅ Rà soát manifest: Đã loại bỏ quyền nguy hiểm `<all_urls>` và thay bằng origin chính xác `['https://*.facebook.com/*']` trong mảng `web_accessible_resources` cũng như host permissions.
- ✅ Kiểm tra không có API key của Gemini/Tavily/FactCheck trong bundle: Đã rà soát thư mục `dist/` - KHÔNG có bất kỳ key nào của LLM hoặc Search API bị rò rỉ ra front-end.
- ✅ Đảm bảo không dùng innerHTML/eval với dữ liệu ngoài: Đã thay thế dòng gán `innerHTML` duy nhất trong `index.ts` thành `textContent` để triệt tiêu mọi khả năng XSS.
- ✅ Thêm Content Security Policy (CSP): Đã thiết lập Content Security Policy cực kì khắt khe cho UI của extension: `script-src 'self'; object-src 'self';` ở trong `manifest.json`.

## Rủi ro còn lại (Known Risks & Vulnerabilities)
1. **Static API Key trong Extension:** Extension của người dùng vẫn đang mang theo 1 key tĩnh (`VITE_EXTENSION_API_KEY`) để định danh và gọi backend của chúng ta. Bất kỳ ai unpack / read file source của extension (trong Chrome) cũng có thể thấy key này và viết bot lấy key đó spam backend của bạn.
   - *Biện pháp giảm thiểu hiện tại*: Đã có Rate Limiting theo IP để làm chậm, và Global Budget để chặn chi phí vượt trần.
   - *Giải pháp lâu dài*: Yêu cầu User đăng nhập (OAuth/Firebase) và dùng Firebase Auth Token hoặc JWT động thay vì tĩnh.
2. **In-Memory Rate Limiting Limit:** Đã đề cập ở trên, bypass được một phần nếu có nhiều backend server node.
3. **Prompt Injection Validation:** Prompts của hệ thống đã tách rời dữ liệu user bằng tag `<post>...</post>` và có explicit system instruction bỏ qua lệnh trong tag. Dù an toàn đến mức cơ bản, với các kĩ thuật bẻ khóa (jailbreak) phức tạp của attacker, Gemini đôi khi vẫn có thể bỏ qua chỉ thị. Chúng ta cần test & review thường xuyên.

## Test đã thêm
- `tests/test_security.py`: Bộ test case chạy thử bằng `FastAPI TestClient`. Bao gồm:
  1. `test_missing_api_key`: Kiểm tra thiếu header `X-API-Key`
  2. `test_rate_limit_ip`: Kiểm tra vượt quá số Request / Phút của 1 IP
  3. `test_rate_limit_key`: Kiểm tra vượt quá Request / Ngày của một key
  4. `test_global_limit`: Kích hoạt Kill switch Global Threshold.
  5. `test_body_too_large`: Thử gửi payload > MAX bytes định mức.
- (Prompt Injection được thử qua các file text nhưng chưa thể assert 100% bằng code do output là LLM sinh, việc kiểm thử cần con người hoặc LLM-evaluator phụ trợ).
