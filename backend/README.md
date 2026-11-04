# Backend API

## Cài đặt

Yêu cầu: Python 3.11+

1. Tạo môi trường ảo:
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# hoặc .venv\Scripts\activate trên Windows
```

2. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

3. Tạo file `.env` từ `.env.example`:
```bash
cp .env.example .env
```

## Chạy server

```bash
uvicorn app.main:app --reload
```

- API Docs (Swagger UI): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Chạy Tests và Linter

- Chạy test:
```bash
pytest
```

- Chạy linter:
```bash
ruff check .
```

## Chọn model và chuyển model khi hết quota

Cấu hình trong `backend/.env` (đọc khi backend khởi động):

```dotenv
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_MODELS=["gemini-3.1-flash-lite","gemini-2.5-flash","gemini-2.5-flash-lite"]
GEMINI_QUOTA_COOLDOWN_SECONDS=60
```

Danh sách trên là cấu hình mẫu; chỉ giữ model được bật và có hạn mức trong project
Google AI Studio của bạn. Tất cả model phải hỗ trợ Interactions API và structured
output. Model mặc định luôn đứng đầu danh sách; các tên trùng được loại bỏ.
`GEMINI_MODELS` phải là JSON array, không phải chuỗi phân cách bằng dấu phẩy.

- `GET /api/v1/models` yêu cầu `X-API-Key`, trả `default_model` và `models`.
  Đọc danh sách không tiêu hao quota phân tích của ứng dụng.
- `POST /api/v1/analyze` nhận thêm `model_id` tùy chọn. Không truyền thì dùng mặc định;
  model ngoài danh sách bị từ chối với HTTP 422.
- Model đã chọn được ưu tiên ở cả bước trích xuất và đánh giá. Khi Gemini trả 429,
  backend chuyển sang model kế tiếp theo vòng, bỏ qua model đang cooldown.
- Cooldown dựa trên RetryInfo/Retry-After nếu có; quota theo ngày chờ đến nửa đêm
  Pacific (có tính DST). Không xác định được loại quota thì dùng cooldown cấu hình.
- Mỗi vòng thử từng model tối đa một lần; giữ timeout 20 giây cho mỗi bước AI.
  Retry lỗi đầu ra JSON vẫn được giữ. Lỗi khác 429 không kích hoạt chuyển model.
- Tất cả model bị giới hạn: HTTP 503 với thông báo và header `Retry-After`.
- Response có `model_usage`: model ưu tiên, model thực tế của từng bước và các model
  đã bỏ qua do quota. Phần đã hoàn thành không chạy lại khi bước tiếp theo đổi model.

Cooldown dùng chung trong một process và mất khi restart. Nếu chạy nhiều worker /
instance, cần lưu cooldown trong Redis hoặc kho dùng chung. Quota Google áp dụng theo
project; chuyển model chỉ hữu ích khi model tiếp theo còn hạn mức, không bảo đảm mọi
model đều có quota độc lập.
