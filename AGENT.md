# AGENT.md

> Hướng dẫn cho AI coding agent (Claude Code, Cursor...) khi làm việc trong dự án này.

## 1. Tổng quan dự án

- **Tên dự án:** Trust Me Bro - Extension kiểm chứng tin tức mạng xã hội
- **Mục tiêu:** Giúp người dùng kiểm tra nhanh độ tin cậy của một đoạn nội dung trên mạng xã hội, có trích dẫn nguồn, ngay tại chỗ (không cần rời khỏi trang).
- **Đối tượng người dùng:** Người dùng mạng xã hội phổ thông, muốn kiểm chứng tin tức/claim trước khi tin hoặc chia sẻ.
- **Trạng thái hiện tại:** MVP — adapter Facebook và Reddit.

## 2. Tech stack

- **Extension (client):** JavaScript/TypeScript, Chrome Extension Manifest V3, Chrome Side Panel API
- **Backend:** Python 3.11+, FastAPI, httpx (gọi API bất đồng bộ)
- **API bên ngoài:** Google Fact Check Tools API, Gemini API, Tavily API
- **Database:** Không dùng ở bản demo này (xử lý real-time, không lưu trữ)
- **Package manager:** npm/pnpm (extension), pip/poetry (backend)
- **Deploy/Hosting:** Chưa chốt (gợi ý: backend deploy dạng container — Railway/Render/Fly.io cho demo)

## 3. Cấu trúc thư mục

```text
/extension
  /src
    /entrypoints        # khởi tạo background, content, side panel
    /features/analysis  # tính năng kiểm chứng: background, content/adapters, sidepanel
    /infrastructure     # HTTP client và adapter Chrome Storage
    /shared             # hợp đồng message và cấu hình dùng chung
  /tests                # module tests, mock Chrome và backend
  /public/icons
/backend
  /app
    /api/v1             # routes
    /core               # config, security, logging
    /services           # từng API bên ngoài: factcheck, gemini, tavily
    /orchestrator       # tổng hợp kết quả
    /schemas            # request/response models
  /tests
```

> Xem chi tiết đầy đủ trong `ARCHITECTURE.md`.

## 4. Quy tắc code

- **Naming:** camelCase cho JS/TS (extension), snake_case cho Python (backend)
- **Comment:** Tiếng Việt cho comment giải thích nghiệp vụ, English cho tên biến/hàm/class
- **Không tự ý thêm dependency mới** nếu chưa xác nhận với người dùng — đặc biệt tránh thêm thư viện nặng không cần thiết cho 1 extension nhỏ
- **Không refactor ngoài phạm vi task** được giao
- **Extension:** dùng module theo tính năng; entrypoint chỉ khởi tạo/đăng ký listener. Không import entrypoint từ tính năng hoặc hạ tầng. Module content không import background/HTTP client; module background không import DOM/UI.
- **TypeScript:** dùng `import type` cho kiểu dữ liệu. Logic của tính năng mới đặt trong `src/features/<tên>/`; chỉ đưa adapter kỹ thuật dùng chung vào `src/infrastructure/`.
- **Hợp đồng:** cập nhật `src/shared/messages.ts` khi thêm message, giữ kiểu dữ liệu của tính năng trong `types.ts`. `SIDEPANEL_PATH` trong `src/shared/config.ts` là đường dẫn chung cho manifest và background.
- **Mỗi service trong `services/` phải implement chung interface** (`base_service.py`) — không viết logic gọi API trực tiếp trong orchestrator hoặc trong route
- **Extension tuyệt đối không chứa API key của Gemini/Tavily/Fact Check** — mọi lời gọi 3 API này chỉ được thực hiện từ backend

## 5. Quy trình làm việc (workflow) mong muốn

1. Đọc kỹ yêu cầu; nếu ảnh hưởng tới kiến trúc (thêm service mới, đổi luồng dữ liệu) → tham khảo `ARCHITECTURE.md` trước
2. Với thay đổi lớn (thêm mạng xã hội mới, đổi cách xác thực...): viết plan ngắn, chờ xác nhận rồi mới code
3. Sau khi code xong: tự chạy lint/test nếu có sẵn cấu hình
4. Tóm tắt ngắn gọn thay đổi sau mỗi task, nêu rõ file nào bị ảnh hưởng
5. Nếu task đụng tới bảo mật (API key, CORS, rate limit) → nhắc lại rule ở mục 6 của `ARCHITECTURE.md` trước khi code

## 6. Testing & Quality Gates

- **Backend:** `pytest`, mock các API bên ngoài (Fact Check/Gemini/Tavily) khi test — không gọi API thật trong test tự động
- **Extension:** `npm test` kiểm tra hợp đồng message, mapping response, trạng thái theo tab và luồng API với mock; chạy thêm `npm run typecheck`, `npm run lint`, `npm run build`. Kiểm tra thủ công trên Chrome theo `extension/README.md`. E2E backend có `test_e2e.py`.
- **Pre-commit / CI:** Dự án sử dụng `pre-commit` framework (ruff, pytest nhanh, eslint, tsc --noEmit, gitleaks). Mọi PR đều được check bởi GitHub Actions `ci.yml`.

Lệnh chạy test backend:
```bash
cd backend
.venv\Scripts\activate  # hoặc source .venv/bin/activate
pytest -m "not e2e"
pytest tests/test_e2e.py
```

## 7. Lệnh thường dùng

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Extension
cd extension
npm ci
npm run build   # build ra dist/ để load unpacked vào Chrome

# Cài đặt Quality Gates (Local)
pip install pre-commit
pre-commit install
```

## 8. Việc KHÔNG được làm

- Không hardcode API key (Gemini/Tavily/Fact Check) trong bất kỳ file nào của `extension/`
- Không commit file `.env` hoặc secrets
- Không push trực tiếp lên nhánh `main`/`production`
- Không lưu nội dung bài đăng của người dùng vào log hoặc file, trừ metadata cần thiết (xem mục bảo mật trong ARCHITECTURE.md)
- Không thay đổi kiến trúc `services/orchestrator` (ví dụ: gọi thẳng API bên ngoài từ route) nếu chưa bàn bạc — sẽ phá vỡ khả năng mở rộng

## 9. Liên kết tài liệu khác

- Kiến trúc kỹ thuật chi tiết: `ARCHITECTURE.md`
- Kế hoạch phát triển: `ROADMAP.md`
