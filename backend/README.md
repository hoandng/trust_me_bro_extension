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
