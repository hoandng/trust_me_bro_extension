# SECURITY_CHECKLIST.md

## Backend
- ✅ `POST /api/v1/analyze` xác thực `X-API-Key` rồi áp dụng mặc định 10 lượt/phút/IP và 100 lượt trong cửa sổ 24 giờ/key. Vượt giới hạn trả `429` cùng `Retry-After`. `GET /api/v1/models` yêu cầu key và chỉ trả tên model cùng model mặc định. Lượt đọc danh sách nằm ngoài các bộ đếm phân tích.
- ✅ `DAILY_ANALYZE_LIMIT_GLOBAL` giới hạn số lượt phân tích đã qua kiểm tra IP/key trong một process theo ngày UTC. Mặc định là 1000 lượt. Một lượt phân tích có thể gọi Gemini nhiều lần do các bước xử lý, retry và chuyển model.
- ✅ Middleware kiểm tra `Content-Length` và trả `413` khi vượt `MAX_BODY_SIZE_BYTES` (mặc định 8192 byte). Giới hạn này dựa trên giá trị header khai báo. Schema phân tích kiểm tra độ dài `text` và từ chối `model_id` ngoài danh sách cấu hình bằng `422`.
- ✅ Middleware gắn `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection` và `Strict-Transport-Security` lên response đi qua `call_next`.
- ✅ `ENV=production` tắt `/docs`, `/redoc` và `/openapi.json`.
- ✅ Exception handler chung trả `{"detail": "Internal server error"}` và ghi thông báo lỗi chung vào application log (không ghi stacktrace). `FactCheckService` và `TavilySearchService` chủ động thay thế `api_key` bằng `***` trong thông báo lỗi nếu xảy ra ngoại lệ HTTP/mạng.
- ⚠️ Formatter JSON trong `app/core/logging.py` tự động che `api_key`, `Authorization: Bearer`, `X-API-Key` và ẩn stacktrace ở mức `ERROR`/`CRITICAL`. Route chỉ log nền tảng và độ dài văn bản, nhưng nhánh lỗi trong `GeminiService` vẫn ghi chuỗi exception hoặc lỗi validation, có thể chứa một phần nội dung trả về từ dịch vụ.

## Extension
- ✅ `vite.config.ts` cấp `sidePanel`, `storage` và host permissions cho Facebook, Reddit và backend. Tài nguyên công khai là icon trên Facebook và Reddit.
- ✅ Mã extension gọi backend bằng `VITE_EXTENSION_API_KEY`. Key của Gemini, Tavily và Fact Check được cấu hình ở backend.
- ✅ Side panel dùng `textContent` cho phần văn bản từ backend. Link nguồn lấy URL từ response và dùng `rel="noopener noreferrer"`.
- ✅ Manifest đặt CSP cho extension pages là `script-src 'self'; object-src 'self';`.
- Nội dung gửi đi và kết quả phân tích nằm trong `chrome.storage.session` theo tab để hiển thị và thử lại. `chrome.storage.local` giữ lựa chọn model.

## Rủi ro còn lại (Known Risks & Vulnerabilities)
1. **Static API Key trong Extension:** Extension của người dùng vẫn đang mang theo 1 key tĩnh (`VITE_EXTENSION_API_KEY`) để định danh và gọi backend của chúng ta. Bất kỳ ai unpack / read file source của extension (trong Chrome) cũng có thể thấy key này và viết bot lấy key đó spam backend của bạn.
   - *Biện pháp giảm thiểu hiện tại*: Đã có Rate Limiting theo IP để làm chậm, và Global Budget để chặn chi phí vượt trần.
   - *Giải pháp lâu dài*: Yêu cầu User đăng nhập (OAuth/Firebase) và dùng Firebase Auth Token hoặc JWT động thay vì tĩnh.
2. **Trạng thái theo process.** Rate limiter và cooldown theo model Gemini nằm trong bộ nhớ của từng process. Các worker đếm và chuyển model độc lập. Khi mọi model đều bị giới hạn quota, API trả `503` cùng `Retry-After`.
3. **Prompt injection.** Prompt đặt nội dung bài đăng trong `<post>...</post>` và yêu cầu Gemini xem nội dung trong thẻ là dữ liệu. Backend kiểm tra cấu trúc JSON và chỉ giữ nhận định nguồn có URL nằm trong tập bằng chứng. Các lớp này giảm rủi ro prompt injection nhưng model vẫn có thể làm theo chỉ thị trong dữ liệu.

## Test đã thêm
- `tests/test_security.py`: Bộ test case chạy thử bằng `FastAPI TestClient`. Bao gồm:
  1. `test_missing_api_key`: Kiểm tra thiếu header `X-API-Key`
  2. `test_rate_limit_ip`: Kiểm tra vượt quá số Request / Phút của 1 IP
  3. `test_rate_limit_key`: Kiểm tra vượt quá Request / Ngày của một key
  4. `test_global_limit`: Kích hoạt Kill switch Global Threshold.
  5. `test_body_too_large`: Thử gửi payload > MAX bytes định mức.
- `backend/tests/test_api.py` kiểm tra xác thực danh sách model, model ngoài danh sách và phản hồi khi hết quota Gemini.
- `backend/tests/test_gemini_service.py` dùng SDK mock để kiểm tra dữ liệu prompt, JSON, lọc URL và chuyển model theo quota. Các test mock kiểm tra hành vi của ứng dụng khi gọi Gemini.
