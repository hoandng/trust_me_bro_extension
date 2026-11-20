# TrustMeBro

TrustMeBro gồm Chrome Extension Manifest V3 và backend FastAPI giúp kiểm chứng độ tin cậy đoạn văn bản trên Facebook và Reddit kèm nguồn đối chứng. Extension gửi văn bản tới backend để trích xuất khẳng định, tra cứu Google Fact Check Tools API và Tavily Search API, sau đó tổng hợp kết luận bằng Gemini Interactions API.

Cập nhật theo commit `f491d97`, 20/11/2026.

## Tính năng

| Tính năng                                                                        | Nền tảng / Phạm vi                                               |
| -------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Bôi đen 20–2000 ký tự hiện nút nổi kiểm chứng                                    | Facebook, Reddit (Chrome / Edge desktop)                         |
| Bóc tách tiêu đề, nội dung, link và chèn nút kiểm chứng bài viết                 | Trang chi tiết bài viết Reddit (`/comments/`)                    |
| Pipeline 3 giai đoạn (trích xuất → tra cứu song song → đánh giá)                 | Backend FastAPI (`AnalysisOrchestrator`)                         |
| Side Panel theo tab, mức chắc chắn 3 vạch, đánh dấu giải thích, sao chép tóm tắt | Extension Side Panel                                             |
| Chọn model Gemini trên UI và tự xoay vòng khi gặp HTTP `429`                     | Extension (`chrome.storage.local`) + Backend (`GeminiModelPool`) |
| Cache kết quả, lưu số liệu vận hành và thống kê admin                            | Backend SQLite (`backend/data/metrics.db`)                       |
| Benchmark 3 chế độ (`llm_only`, `llm_factcheck`, `full`)                         | CLI Python (`scripts/benchmark/run_benchmark.py`)                |

## Yêu cầu hệ thống

- **Python 3.12+** (`backend/Dockerfile` dùng `python:3.12-slim`, CI dùng `3.13`).
- **Node.js 22.13+** và `npm` (`package-lock.json` hỗ trợ `20.19+`, `22.13+`, `24+`; CI dùng `20`, Docker và test dùng `22`).
- Trình duyệt Chromium hỗ trợ Manifest V3 và Side Panel API (Chrome / Edge).
- Các khóa API: Google Gemini, Tavily Search, Google Fact Check Tools.

## Cài đặt và chạy

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # PowerShell: Copy-Item .env.example .env
# Điền GEMINI_API_KEY, TAVILY_API_KEY, FACTCHECK_API_KEY, EXTENSION_API_KEY trong backend/.env
uvicorn app.main:app --reload --no-proxy-headers
```

### Extension

```bash
cd extension
npm ci
cp .env.example .env               # PowerShell: Copy-Item .env.example .env
# Đặt VITE_EXTENSION_API_KEY trùng EXTENSION_API_KEY trong backend/.env
npm run build                      # Xuất ra extension/dist/ (hoặc npm run dev để watch)
```

### Khởi động nhanh và nạp vào trình duyệt

- **Windows:** chạy `.\dev.ps1` hoặc `dev.bat` tại thư mục gốc để mở song song `uvicorn` và `npm run dev`.
- **Docker Compose:** tạo `backend/.env` rồi chạy `docker compose up --build` (mount `backend/data` và xuất extension vào `extension/dist`).
- Mở `chrome://extensions/`, bật **Developer mode**, chọn **Load unpacked** trỏ tới `extension/dist/`.
- Sao chép Extension ID, đặt `ALLOWED_ORIGINS=chrome-extension://<extension-id>` trong `backend/.env` và khởi động lại backend.

## Cấu hình

Biến backend đọc từ `backend/.env` (`backend/app/core/config.py`); biến extension đọc từ `extension/.env` khi build:

| Biến                                | Bắt buộc | Mặc định                  | Ý nghĩa                                                                       |
| ----------------------------------- | -------- | ------------------------- | ----------------------------------------------------------------------------- |
| `GEMINI_API_KEY`                    | Có       | `""`                      | Khóa Google Gemini API (Interactions API)                                     |
| `TAVILY_API_KEY`                    | Có       | `""`                      | Khóa Tavily Search API                                                        |
| `FACTCHECK_API_KEY`                 | Có       | `""`                      | Khóa Google Fact Check Tools API                                              |
| `EXTENSION_API_KEY`                 | Có       | `""`                      | Khóa xác thực header `X-API-Key` của extension                                |
| `ADMIN_API_KEY`                     | Không    | `""`                      | Khóa `X-Admin-API-Key` cho `/api/v1/stats/summary` (khác `EXTENSION_API_KEY`) |
| `ALLOWED_ORIGINS`                   | Không    | `""`                      | Các origin CORS cách nhau bởi dấu phẩy                                        |
| `GEMINI_MODEL`                      | Không    | `gemini-3.1-flash-lite`   | Model Gemini mặc định                                                         |
| `GEMINI_MODELS`                     | Không    | `[]`                      | Mảng JSON danh sách model Gemini dự phòng khi xoay vòng                       |
| `GEMINI_QUOTA_COOLDOWN_SECONDS`     | Không    | `60`                      | Thời gian cooldown tối thiểu (giây) khi model gặp HTTP `429`                  |
| `TAVILY_INCLUDE_DOMAINS`            | Không    | `[]`                      | Mảng JSON tên miền ưu tiên khi tra cứu Tavily                                 |
| `TAVILY_EXCLUDE_DOMAINS`            | Không    | `[]`                      | Mảng JSON tên miền loại trừ khi tra cứu Tavily                                |
| `SEARCH_QUERY_LIMIT`                | Không    | `2`                       | Số truy vấn tối đa mỗi nhà cung cấp tìm kiếm (`1`–`2`)                        |
| `METRICS_DB_PATH`                   | Không    | `backend/data/metrics.db` | Đường dẫn SQLite lưu số liệu, feedback và cache                               |
| `GEMINI_TOKEN_PRICES`               | Không    | `{}`                      | JSON đơn giá USD / 1 triệu token theo tên model                               |
| `TAVILY_USD_PER_CREDIT`             | Không    | Chưa đặt                  | Đơn giá USD trên mỗi credit Tavily                                            |
| `RATE_LIMIT_PER_MINUTE_IP`          | Không    | `10`                      | Giới hạn lượt gọi mỗi phút theo IP                                            |
| `TRUST_PROXY_HEADERS`               | Không    | `false`                   | Bật đọc `X-Forwarded-For` khi đứng sau proxy tin cậy                          |
| `TRUSTED_PROXY_NETWORKS`            | Không    | `[]`                      | Mảng JSON IP/CIDR của reverse proxy tin cậy                                   |
| `RATE_LIMIT_PER_DAY_KEY`            | Không    | `100`                     | Giới hạn lượt gọi trong 24 giờ theo `X-API-Key` (miễn cache hit)              |
| `DAILY_ANALYZE_LIMIT_GLOBAL`        | Không    | `1000`                    | Trần tổng lượt mỗi ngày UTC trên một process                                  |
| `MAX_BODY_SIZE_BYTES`               | Không    | `8192`                    | Giới hạn `Content-Length` của request body (byte)                             |
| `ANALYSIS_TIMEOUT_SECONDS`          | Không    | `25.0`                    | Ngân sách thời gian (giây) cho toàn bộ pipeline                               |
| `CACHE_HIGH_CONFIDENCE_TTL_SECONDS` | Không    | `86400`                   | TTL cache (giây) khi `confidence_score >= 0.8` (trừ `unverified`)             |
| `CACHE_LOW_CONFIDENCE_TTL_SECONDS`  | Không    | `3600`                    | TTL cache (giây) khi `confidence_score < 0.8` (trừ `unverified`)              |
| `CACHE_UNVERIFIED_TTL_SECONDS`      | Không    | `900`                     | TTL cache (giây) cho verdict `unverified`                                     |
| `ENV`                               | Không    | `development`             | Đặt `production` để tắt `/docs`, `/redoc`, `/openapi.json`                    |
| `VITE_BACKEND_URL`                  | Không    | `http://127.0.0.1:8000`   | URL backend cho extension (`vite.config.ts` đọc từ `process.env`)             |
| `VITE_EXTENSION_API_KEY`            | Có       | `""`                      | Khóa gửi qua `X-API-Key`, phải trùng `EXTENSION_API_KEY`                      |

## Kiểm thử

```bash
# Backend (từ backend/, đã kích hoạt .venv; toàn bộ API ngoài được mock)
ruff check .
pytest -m "not e2e"
pytest tests/test_e2e.py

# Extension (từ extension/)
npm run lint
npm run typecheck
npm test
npm run build
```

## Cấu trúc thư mục

```text
trust-me-bro/
├── backend/    # FastAPI API, orchestrator, services, SQLite storage, pytest
├── extension/  # Chrome Extension MV3 (TypeScript, Vite, tests mock)
├── scripts/    # Script thử từng API và bộ benchmark 3 chế độ
├── docs/       # Báo cáo môn học và kiểm toán tài liệu (DOC_AUDIT.md)
└── .github/    # Workflow CI (ci.yml) và cấu hình Dependabot
```

## Tài liệu liên quan

- [ARCHITECTURE.md](ARCHITECTURE.md) — Thành phần, hợp đồng API, quy tắc pipeline, lưu trữ và phụ thuộc lớp.
- [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md) — Mối đe doạ, biện pháp đang có, dữ liệu truyền/lưu và xử lý lộ khoá.
- [ROADMAP.md](ROADMAP.md) — Trạng thái hạng mục hiện tại, kế hoạch tiếp theo và ngoài phạm vi.
- [AGENT.md](AGENT.md) — Quy ước phát triển, kiểm thử và nhánh/commit cho người đóng góp và AI agent.
- [PROMPTS.md](PROMPTS.md) — Thư viện prompt làm việc và trạng thái các task khởi tạo.
- [backend/README.md](backend/README.md) — Hướng dẫn vận hành backend, reverse proxy và xoay vòng model.
- [extension/README.md](extension/README.md) — Hướng dẫn build Vite, debug và kiểm tra thủ công extension.
- [scripts/benchmark/README.md](scripts/benchmark/README.md) — Hướng dẫn chạy benchmark 3 chế độ.
- [BUSINESS.md](BUSINESS.md) — Bài toán kinh doanh, phân khúc khách hàng và giả định KPI.

## Giấy phép

Thư mục gốc chưa có file `LICENSE`; riêng `extension/package.json` khai báo `"license": "ISC"`. Xem mục cần xác nhận tại [docs/DOC_AUDIT.md](docs/DOC_AUDIT.md).
