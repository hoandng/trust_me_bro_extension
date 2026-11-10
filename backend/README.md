# Backend API

## Cài đặt

Yêu cầu Python 3.11+. Chạy các lệnh sau từ thư mục `backend/`.

1. Tạo môi trường ảo:
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# PowerShell: .\.venv\Scripts\Activate.ps1
```

2. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

3. Tạo file `.env` từ `.env.example`:
```bash
cp .env.example .env  # PowerShell: Copy-Item .env.example .env
```

4. Điền `GEMINI_API_KEY`, `TAVILY_API_KEY` và `FACTCHECK_API_KEY`. Đặt `EXTENSION_API_KEY` trùng với `VITE_EXTENSION_API_KEY` khi build extension và khai báo `ALLOWED_ORIGINS` theo ID tiện ích. Có thể phân cách nhiều origin bằng dấu phẩy.

## Chạy server

```bash
uvicorn app.main:app --reload
```

- Kiểm tra trạng thái bằng `GET /health`.
- Xem Swagger UI tại `http://127.0.0.1:8000/docs` hoặc ReDoc tại `http://127.0.0.1:8000/redoc`. `ENV=production` tắt cả hai trang và `/openapi.json`.

## API

| Endpoint | Hành vi |
|---|---|
| `GET /health` | Trả `{"status":"ok"}` để kiểm tra tiến trình FastAPI. |
| `GET /api/v1/models` | Yêu cầu `X-API-Key`. Trả `default_model` và `models` theo thứ tự cấu hình. |
| `POST /api/v1/analyze` | Yêu cầu `X-API-Key`. Nhận `text` dài 20–2000 ký tự, `platform` (`facebook`, `reddit`, `x`) và các trường tùy chọn `page_url`, `lang`, `model_id`. |

Các giới hạn `RATE_LIMIT_PER_MINUTE_IP` (10), `RATE_LIMIT_PER_DAY_KEY` (100) và `DAILY_ANALYZE_LIMIT_GLOBAL` (1000 mỗi process) áp dụng cho phân tích. Khi vượt giới hạn, API trả `429` cùng `Retry-After`. `GET /api/v1/models` chỉ xác thực key. Xem [kiến trúc và ví dụ response](../ARCHITECTURE.md#23-luồng-xử-lý-tại-orchestrator).

## Biến môi trường (`app/core/config.py`)

| Biến môi trường | Mặc định | Mô tả |
|---|---|---|
| `GEMINI_API_KEY` | `""` | API key cho Google Gemini (Interactions API). |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Model Gemini mặc định (được đưa lên đầu danh sách khả dụng). |
| `GEMINI_MODELS` | `[]` | Mảng JSON danh sách các model Gemini dự phòng theo thứ tự xoay vòng. |
| `GEMINI_QUOTA_COOLDOWN_SECONDS` | `60` | Thời gian cooldown tối thiểu (giây) khi một model trả về HTTP `429`. |
| `TAVILY_API_KEY` | `""` | API key cho Tavily Search API. |
| `TAVILY_INCLUDE_DOMAINS` | `[]` | Mảng JSON các domain ưu tiên khi tìm kiếm qua Tavily. |
| `TAVILY_EXCLUDE_DOMAINS` | `[]` | Mảng JSON các domain loại trừ khi tìm kiếm qua Tavily. |
| `FACTCHECK_API_KEY` | `""` | API key cho Google Fact Check Tools API. |
| `EXTENSION_API_KEY` | `""` | Khóa xác thực nội bộ giữa Extension và Backend qua header `X-API-Key`. |
| `ALLOWED_ORIGINS` | `""` | Danh sách origin được phép gọi CORS (phân tách bằng dấu phẩy, ví dụ `chrome-extension://<id>`). |
| `RATE_LIMIT_PER_MINUTE_IP` | `10` | Giới hạn số lượt phân tích mỗi phút trên một IP. |
| `RATE_LIMIT_PER_DAY_KEY` | `100` | Giới hạn số lượt phân tích trong cửa sổ 24 giờ trên một `X-API-Key`. |
| `DAILY_ANALYZE_LIMIT_GLOBAL` | `1000` | Hạn mức tổng số lượt phân tích mỗi ngày UTC trên một process (kill switch bảo vệ chi phí). |
| `MAX_BODY_SIZE_BYTES` | `8192` | Dung lượng tối đa của request body (byte) kiểm tra qua `Content-Length`. |
| `ENV` | `development` | Môi trường chạy (`production` sẽ tắt `/docs`, `/redoc` và `/openapi.json`). |

## Chạy Tests, Linter và Script thử nghiệm

- Chạy toàn bộ unit/integration/e2e test (các dịch vụ bên ngoài được mock hoàn toàn):
```bash
pytest
```

- Chạy linter:
```bash
ruff check .
```

- Chạy thử từng service thật từ thư mục gốc (cần cấu hình key thật trong `backend/.env`):
```bash
python scripts/try_factcheck.py "Donald Trump won the 2020 election"
python scripts/try_tavily.py "Latest news on artificial intelligence"
python scripts/try_gemini.py
```

## Chọn model và chuyển model khi hết quota

Cấu hình trong `backend/.env` (đọc khi backend khởi động):

```dotenv
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_MODELS=["gemini-3.1-flash-lite","gemini-3.5-flash","gemini-2.5-flash-lite"]
GEMINI_QUOTA_COOLDOWN_SECONDS=60
```

Danh sách trên là cấu hình mẫu. Chỉ giữ model được bật và có hạn mức trong project
Google AI Studio của bạn. Tất cả model phải hỗ trợ Interactions API và structured
output. Backend đưa model mặc định lên đầu và loại tên trùng. Khai báo
`GEMINI_MODELS` dưới dạng mảng JSON. Nếu để trống danh sách (`[]`) hoặc bỏ biến này,
backend chỉ dùng `GEMINI_MODEL`.

- `POST /api/v1/analyze` dùng model mặc định khi bỏ qua `model_id` và trả HTTP 422
  nếu model được yêu cầu nằm ngoài danh sách.
- Model đã chọn được ưu tiên ở cả bước trích xuất và đánh giá. Khi Gemini trả 429,
  backend chuyển sang model kế tiếp theo vòng, bỏ qua model đang cooldown.
- Cooldown lấy giá trị lớn nhất giữa mức cấu hình (tối thiểu 1 giây), `RetryInfo`,
  `Retry-After` dạng số giây và thời gian đến nửa đêm Pacific nếu Gemini báo quota ngày.
- Mỗi vòng thử từng model tối đa một lần. Mỗi bước AI có timeout 20 giây và tối đa
  hai lần thử khi đầu ra trống, JSON không hợp lệ hoặc gặp lỗi ngoài quota. Chỉ HTTP 429
  của Gemini mới đưa model vào cooldown và kích hoạt chuyển model.
- Khi tất cả model chạm hạn mức, backend trả HTTP 503 với thông báo và header `Retry-After`.
- Response phân tích có `model_usage` với `requested_model`, `extraction_model`,
  `assessment_model` và `fallbacks`. Trường model của một bước có thể là `null` khi
  bước đó chưa nhận được phản hồi từ Gemini. Phần đã hoàn thành được giữ lại khi bước
  tiếp theo đổi model.

Cooldown dùng chung trong một process và mất khi restart. Các worker và instance
theo dõi cooldown độc lập. Việc chuyển model chỉ giúp tiếp tục xử lý khi model tiếp
theo còn hạn mức trong project.
