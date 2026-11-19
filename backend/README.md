# Backend API

Hướng dẫn vận hành, cấu hình reverse proxy, xoay vòng model và chạy kiểm thử cho dịch vụ FastAPI trong `backend/`.

Cập nhật: 19/11/2026.

## Cài đặt, cấu hình và kiến trúc

Xem yêu cầu Python, lệnh cài đặt và bảng đầy đủ biến môi trường tại [README.md](../README.md). Xem danh sách endpoint, schema, quy tắc pipeline và lưu trữ SQLite (`metrics.db`) tại [ARCHITECTURE.md](../ARCHITECTURE.md). Xem kiểm soát bảo mật tại [SECURITY_CHECKLIST.md](../SECURITY_CHECKLIST.md).

## Chạy server

Chạy từ thư mục `backend/` sau khi kích hoạt `.venv`:

```bash
uvicorn app.main:app --reload --no-proxy-headers
```

- Kiểm tra tiến trình bằng `GET http://127.0.0.1:8000/health`.
- Swagger UI ở `/docs` và ReDoc ở `/redoc` tự tắt cùng `/openapi.json` khi đặt `ENV=production`.
- Docker dùng `backend/Dockerfile` (`python:3.12-slim`) hoặc `docker compose up --build` từ thư mục gốc.

## Chạy sau reverse proxy

Giữ cờ `--no-proxy-headers` cho Uvicorn để FastAPI nhận IP kết nối trực tiếp (`request.client.host`). Khi triển khai sau reverse proxy:

1. Đặt `TRUST_PROXY_HEADERS=true` và khai báo `TRUSTED_PROXY_NETWORKS` là mảng JSON các IP hoặc CIDR của proxy tin cậy (ví dụ `["127.0.0.1/32"]`).
2. Cấu hình proxy ngoài cùng ghi đè `X-Forwarded-For` bằng IP client quan sát được; các proxy phía sau nối thêm IP hop trước vào cuối chuỗi.
3. Chặn kết nối trực tiếp tới cổng backend từ ngoài danh sách proxy tin cậy.

## Cấu hình xoay vòng model Gemini

Ví dụ khai báo trong `backend/.env`:

```dotenv
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_MODELS=["gemini-3.1-flash-lite","gemini-3.5-flash","gemini-2.5-flash-lite"]
GEMINI_QUOTA_COOLDOWN_SECONDS=60
```

Chỉ liệt kê các model được bật trong project Google AI Studio và hỗ trợ Interactions API cùng Structured Output. Nếu bỏ trống `GEMINI_MODELS`, backend chỉ dùng `GEMINI_MODEL`. Quy tắc cooldown, fallback và giới hạn thời gian từng bước (`stage_cap = max(20.0, ANALYSIS_TIMEOUT_SECONDS * 0.6)`) xem tại [ARCHITECTURE.md](../ARCHITECTURE.md).

## Kiểm thử và script chạy thử dịch vụ

```bash
# Chạy từ thư mục backend/ (toàn bộ API ngoài được mock)
ruff check .
pytest -m "not e2e"
pytest tests/test_e2e.py
```

Chạy thử từng dịch vụ thật từ thư mục gốc (tiêu tốn hạn mức API bằng khóa trong `backend/.env`):

```bash
python scripts/try_factcheck.py "Donald Trump won the 2020 election"
python scripts/try_tavily.py "Latest news on artificial intelligence"
python scripts/try_gemini.py
```
