# Trust Me Bro

**Trust Me Bro** là Chrome Extension (Manifest V3) kết hợp Backend AI (FastAPI) giúp người dùng kiểm chứng nhanh độ tin cậy của bài đăng hoặc đoạn văn bản ngay trên mạng xã hội (Facebook, Reddit) mà không cần rời khỏi trang đang đọc.

---

## Tính năng chính

- **Kiểm chứng trực tiếp trên trang (Facebook & Reddit):**
  - Bôi đen đoạn văn bản dài **20–2000 ký tự** trên Facebook hoặc Reddit để hiển thị nút nổi kiểm chứng ngay phía trên vùng chọn.
  - Trên trang chi tiết bài viết Reddit (`/comments/`), extension tự động bóc tách tiêu đề, nội dung, link bài báo (`content-href`) và chèn nút **"Kiểm chứng bài viết"**.
- **Pipeline phân tích 3 giai đoạn tại Backend:**
  - **Stage 0 — Trích xuất & Lọc (Gemini Interactions API):** Tách khẳng định chính (`main_claim`), nhận diện ngôn ngữ, sinh tối đa 3 truy vấn tìm kiếm và lọc các nội dung không thể kiểm chứng (`is_checkable=false` như ý kiến cá nhân, câu hỏi, quảng cáo).
  - **Stage 1 — Thu thập bằng chứng song song:** Truy vấn đồng thời **Google Fact Check Tools API** (chuẩn hóa nhãn đánh giá tiếng Anh & tiếng Việt) và **Tavily Search API** (`news` → fallback `general`), sau đó gộp và xếp hạng nguồn theo độ uy tín (`trusted_domains.json`).
  - **Stage 2 — Tổng hợp & Đánh giá (Gemini Interactions API):** Đối chiếu bằng chứng theo độ tin cậy nguồn và mốc thời gian xuất bản, sinh kết luận (`likely_true`, `likely_false`, `mixed`, `unverified`), điểm tin cậy và giải thích tiếng Việt ngắn gọn có đánh dấu inline (`✓` / `✗` / `?`).
- **Side Panel UI trực quan theo từng tab:**
  - Theo dõi trạng thái độc lập cho từng tab (`idle` → `loading` → `success` / `error`), không lưu nội dung bài đăng vào Chrome Storage.
  - Hiển thị banner kết luận dễ hiểu (*Có vẻ đúng*, *Có vẻ sai sự thật*, *Đúng một phần*, *Chưa đủ bằng chứng*), mức chắc chắn **3 vạch** (*Thấp* / *Vừa* / *Cao*), giải thích kèm chú thích trực quan, danh sách nguồn với thái độ (*Ủng hộ* / *Phản bác* / *Liên quan*), cảnh báo khi có dịch vụ gặp sự cố, chi tiết kỹ thuật và nút **Sao chép để chia sẻ**.
- **Chọn model Gemini & tự động chuyển khi chạm hạn mức:**
  - Người dùng có thể mở mục Cài đặt trên Side Panel để chọn model ưu tiên (lưu ở `chrome.storage.local`).
  - Khi một model gặp HTTP `429`, backend đặt cooldown theo model trong process và tự động xoay vòng sang model khả dụng tiếp theo.
- **Cache kết quả & Lưu số liệu vận hành:**
  - Backend cache kết quả hợp lệ trong SQLite theo hash nội dung chuẩn hóa, phiên bản prompt, model và ngôn ngữ để giảm chi phí và độ trễ.
  - Lưu metadata phân tích (không lưu nội dung gốc bài đăng) phục vụ thống kê vận hành (`/api/v1/stats/summary`).
  - *Lưu ý:* Khối đánh giá 5 sao trên UI Side Panel hiện đang tắt gửi mạng qua cờ `FEEDBACK_ENDPOINT_ENABLED = false` trong lúc chờ đồng bộ schema với endpoint `POST /api/v1/feedback` (`helpful`, `reason`) ở backend.

---

## Tổng quan kiến trúc

Dự án áp dụng mô hình **Client–Server** để tách phần giao diện/DOM khỏi logic AI và bảo vệ toàn bộ API key của bên thứ ba ở backend:

- **`extension/` (Client):** Chrome Extension Manifest V3 viết bằng TypeScript strict, HTML/CSS và DOM thuần, build bằng Vite theo kiến trúc module theo tính năng (`entrypoints/`, `features/analysis/`, `infrastructure/`, `shared/`). Xem [hướng dẫn extension](extension/README.md).
- **`backend/` (Server):** REST API bằng Python + FastAPI (`app/api/`, `app/orchestrator/`, `app/services/`, `app/core/`, `app/prompts/`, `app/schemas/`) kèm SQLite cho số liệu, phản hồi và cache. Xem [hướng dẫn backend](backend/README.md).
- **`scripts/`:** Các script thử nghiệm từng dịch vụ (`try_factcheck.py`, `try_tavily.py`, `try_gemini.py`) và bộ công cụ benchmark 3 chế độ (`scripts/benchmark/`). Xem [hướng dẫn benchmark](scripts/benchmark/README.md).

Xem chi tiết thiết kế hệ thống và luồng xử lý tại [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Cài đặt & Chạy dự án

### 1. Yêu cầu môi trường

- **Python 3.11+** (Docker dùng `python:3.12-slim`, CI dùng `3.13`).
- **Node.js** `20.19+` (nhánh 20), `22.13+` (nhánh 22) hoặc `24+` và `npm`.
- Các API key từ nhà cung cấp:
  - Google Gemini API Key
  - Tavily Search API Key
  - Google Fact Check Tools API Key

### 2. Thiết lập & Chạy Backend

```bash
cd backend
python -m venv .venv

# Kích hoạt môi trường ảo
source .venv/bin/activate        # macOS / Linux
# .\.venv\Scripts\Activate.ps1   # PowerShell (Windows)

pip install -r requirements.txt
cp .env.example .env             # PowerShell: Copy-Item .env.example .env
```

Cấu hình `backend/.env` với `GEMINI_API_KEY`, `TAVILY_API_KEY`, `FACTCHECK_API_KEY`, đặt `EXTENSION_API_KEY` (khóa dùng chung với extension) và `ADMIN_API_KEY` (khác `EXTENSION_API_KEY` nếu bật endpoint thống kê).

Khởi động FastAPI:

```bash
uvicorn app.main:app --reload --no-proxy-headers
```

Backend mặc định chạy tại `http://127.0.0.1:8000` (kiểm tra nhanh qua `GET /health`).

### 3. Thiết lập & Build Extension

Mở terminal khác tại thư mục gốc dự án:

```bash
cd extension
npm ci
cp .env.example .env             # PowerShell: Copy-Item .env.example .env
```

Đảm bảo `VITE_EXTENSION_API_KEY` trong `extension/.env` trùng với `EXTENSION_API_KEY` trong `backend/.env`, sau đó build:

```bash
npm run build    # Tạo thư mục extension/dist/
# hoặc chạy watcher khi phát triển:
npm run dev
```

### 4. Khởi động nhanh (Windows / Docker)

- **Windows (PowerShell / CMD):** chạy `.\dev.ps1` hoặc `dev.bat` tại thư mục gốc để mở song song cửa sổ Backend (`uvicorn`) và Extension watcher (`npm run dev`).
- **Docker Compose:** chạy `docker compose up --build` (cần có `backend/.env`; tự mount `backend/data` để giữ `metrics.db` và chạy thêm service `extension-builder` xuất ra `extension/dist`).

### 5. Nạp Extension vào trình duyệt

1. Mở `chrome://extensions/` (Chrome) hoặc `edge://extensions/` (Edge).
2. Bật **Developer mode**.
3. Chọn **Load unpacked** và trỏ tới thư mục `extension/dist/`.
4. Sao chép **Extension ID**, cập nhật `ALLOWED_ORIGINS=chrome-extension://<extension-id>` trong `backend/.env` rồi khởi động lại backend.
5. Mở (hoặc tải lại) tab Facebook hoặc Reddit, bôi đen đoạn văn bản 20–2000 ký tự để bấm nút nổi kiểm chứng, hoặc bấm **"Kiểm chứng bài viết"** tại trang chi tiết bài đăng Reddit.

---

## Kiểm thử & Chất lượng mã

```bash
# Backend (từ thư mục backend/, đã kích hoạt .venv)
pytest
ruff check .

# Extension (từ thư mục extension/)
npm test
npm run typecheck
npm run lint
```

---

## Tài liệu liên quan

- [ARCHITECTURE.md](ARCHITECTURE.md) — Kiến trúc kỹ thuật, cấu trúc module và luồng xử lý chi tiết.
- [ROADMAP.md](ROADMAP.md) — Tiến độ hiện tại và lộ trình phát triển.
- [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md) — Các lớp kiểm soát bảo mật, quyền riêng tư và rủi ro còn lại.
- [BUSINESS.md](BUSINESS.md) — Bài toán kinh doanh, phân khúc khách hàng và KPI.
- [backend/README.md](backend/README.md) — Chi tiết API, biến môi trường và cơ chế xoay vòng model.
- [extension/README.md](extension/README.md) — Chi tiết kiến trúc client, build Vite và debug trên trình duyệt.
- [scripts/benchmark/README.md](scripts/benchmark/README.md) — Hướng dẫn chạy benchmark 3 chế độ.
