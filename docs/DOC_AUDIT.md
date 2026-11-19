# DOC_AUDIT

Báo cáo kiểm kê tài liệu, ma trận mâu thuẫn, khẳng định đã xoá, lỗi mã nguồn ghi nhận (không sửa), quyết định cần người và kết quả chạy thử lệnh của repo TrustMeBro.

Cập nhật theo commit `16c4a3f`, 19/11/2026 (đối chiếu cả 3 file mã nguồn đang có thay đổi ở working tree: `backend/app/core/trusted_domains.json`, `backend/app/prompts/gemini_prompts.py`, `backend/tests/test_source_ranking.py`).

## 1. Kiểm kê tài liệu

| File | Mục đích | Commit / ngày trước sửa | Tình trạng trước đồng bộ | Xử lý |
|---|---|---|---|---|
| `README.md` | Tổng quan, cài đặt, cấu hình, lệnh chạy | `826bdd0` (2026-11-19) | Thiếu dòng commit trên header | Cập nhật header theo commit `16c4a3f` (132 dòng) |
| `ARCHITECTURE.md` | Thành phần, API, pipeline, lưu trữ, phụ thuộc | `026f81a` (2026-11-19) | Đã cập nhật feedback mới nhưng thiếu dòng commit | Cập nhật header theo commit `16c4a3f` (160 dòng) |
| `SECURITY_CHECKLIST.md` | Mối đe doạ, biện pháp, rủi ro, xử lý lộ khoá | `826bdd0` (2026-11-19) | Lỗi thời ở bảng `feedback`, còn ghi `FEEDBACK_ENDPOINT_ENABLED = false` và thiếu `RequestValidationError` lược `input` | Cập nhật khớp `metrics.py`, `main.py`, `config.ts` (51 dòng) |
| `ROADMAP.md` | Trạng thái hạng mục, kế hoạch, ngoài phạm vi | `826bdd0` (2026-11-19) | Còn xếp feedback là `Đang làm` và ghi lệch schema | Chuyển feedback sang `Đã làm` và cập nhật header (45 dòng) |
| `AGENT.md` | Quy ước làm việc cho AI agent và người đóng góp | `826bdd0` (2026-11-19) | Lỗi thời: nhắc lệnh không tồn tại `python scripts/docs_sync.py --check` và bảng không có trong repo | Xoá mục không kiểm chứng được, cập nhật header (58 dòng) |
| `PROMPTS.md` | Thư viện prompt khởi tạo T0–T15 | `826bdd0` (2026-11-19) | Thiếu dòng commit trên header | Cập nhật header theo commit `16c4a3f` (552 dòng) |
| `BUSINESS.md` | Bài toán kinh doanh, phân khúc, giả định KPI | `826bdd0` (2026-11-19) | Mục ưu tiên P1 còn ghi feedback là `Đang làm` | Tách trạng thái feedback (`Đã làm`) và pilot (`Dự kiến`), cập nhật header (114 dòng) |
| `backend/README.md` | Hướng dẫn vận hành backend | `826bdd0` (2026-11-19) | Thiếu dòng commit trên header | Cập nhật header theo commit `16c4a3f` (58 dòng) |
| `extension/README.md` | Hướng dẫn build/debug extension | `826bdd0` (2026-11-19) | Bước kiểm tra thủ công còn ghi `FEEDBACK_ENDPOINT_ENABLED = false` | Sửa thành `FEEDBACK_ENDPOINT_ENABLED = true`, cập nhật header (51 dòng) |
| `scripts/benchmark/README.md` | Hướng dẫn chạy benchmark 3 chế độ | `826bdd0` (2026-11-19) | Đồng bộ theo `b00372f` | Cập nhật header theo commit `16c4a3f` (55 dòng) |
| `scripts/DATA_GUIDE.md` | Đặc tả định dạng CSV benchmark | `826bdd0` (2026-11-19) | Thiếu câu mô tả mục đích và dòng commit | Khôi phục header và dòng commit `16c4a3f` (44 dòng) |
| `docs/PROJECT_CHARTER.md` | Tài liệu môn học (Project Charter) | `b00372f` (2026-11-18) | Ngoài phạm vi đồng bộ tài liệu kỹ thuật | Không sửa |
| `docs/FINAL_REPORT.md` | Báo cáo cuối kỳ môn học | `b00372f` (2026-11-18) | Ngoài phạm vi đồng bộ tài liệu kỹ thuật | Không sửa |
| `docs/DOC_TODO.md` | Danh sách chỗ trống cho Charter & Final Report | `b00372f` (2026-11-18) | Thuộc nhóm báo cáo môn học (chưa phản ánh thay đổi feedback/trusted_domains sau `b00372f`) | Không sửa |

## 2. Ma trận mâu thuẫn

| Thông tin | Nơi A nói | Nơi B nói | Sự thật theo code | Xử lý |
|---|---|---|---|---|
| Trạng thái và schema `/api/v1/feedback` | `SECURITY_CHECKLIST.md`, `ROADMAP.md`, `BUSINESS.md`, `extension/README.md`: lệch schema và tắt bằng `FEEDBACK_ENDPOINT_ENABLED = false` | `ARCHITECTURE.md`: đã bật `FEEDBACK_ENDPOINT_ENABLED = true`, nhận `{rating, comment}` | Commit `026f81a` và `16c4a3f`: `metrics.py` nhận `{request_id, rating, comment?}` + tương thích `{helpful, reason?}`, `main.py` lọc `input` khi 422, `config.ts` bật `true` | Đồng bộ toàn bộ 4 tài liệu khớp `ARCHITECTURE.md` |
| Script kiểm tra tài liệu `scripts/docs_sync.py` | `AGENT.md` (từ `826bdd0`): yêu cầu chạy `python scripts/docs_sync.py --check` | Không có file này trong repo | `scripts/` chỉ có `DATA_GUIDE.md`, `try_*.py` và `benchmark/` | Xoá khẳng định không tồn tại khỏi `AGENT.md` |
| Số tên miền trong `trusted_domains.json` | Tài liệu cũ trước `826bdd0`: 4 tên miền quốc tế | Working tree + `ARCHITECTURE.md` | `backend/app/core/trusted_domains.json` (working tree) có 32 tên miền (17 `tier1`, 15 `tier2`, 32 `display_names`, gồm 28 tên miền Việt Nam) | Giữ thống nhất 32 tên miền (28 Việt Nam) |
| Lược bỏ `input` trong lỗi `422` | `SECURITY_CHECKLIST.md`: chưa ghi nhận | `ARCHITECTURE.md`: `validation_exception_handler` lược bỏ `input` | `backend/app/main.py:80-86` đăng ký handler cho `RequestValidationError` | Bổ sung vào `SECURITY_CHECKLIST.md` |
| Dòng commit ở đầu tài liệu | Toàn bộ 11 file bị mất dòng `Cập nhật theo commit` trong `826bdd0` | Yêu cầu định dạng tài liệu kỹ thuật | Commit hiện tại là `16c4a3f` (19/11/2026) | Khôi phục dòng `Cập nhật theo commit \`16c4a3f\`, 19/11/2026.` ở mọi file |
| Phiên bản Python & Node | Tài liệu cũ: Python `3.11+`, Node `20+` | CI (`3.13` / `20`), Dockerfile (`3.12`), docker-compose/lockfile (`22`) | `package-lock.json` yêu cầu Node `^20.19.0 \|\| ^22.13.0 \|\| >=24`; Dockerfile dùng `python:3.12-slim` | Giữ thống nhất Python `3.12+`, Node `22.13+` tại `README.md` |
| Giấy phép | `extension/package.json`: `"license": "ISC"` | Root repo: không có file `LICENSE` | Chưa có file `LICENSE` ở thư mục gốc | Ghi đúng thực tế ở `README.md`, chờ người quyết định |

## 3. Khẳng định đã xoá vì không kiểm chứng được

- Lệnh `python scripts/docs_sync.py --check` và tham chiếu tới bảng "Thay đổi → tài liệu" trong `AGENT.md` (không tồn tại trong mã nguồn).
- Rủi ro còn lại và mô tả cũ về việc tắt `FEEDBACK_ENDPOINT_ENABLED = false` trong `SECURITY_CHECKLIST.md`, `ROADMAP.md`, `BUSINESS.md` và `extension/README.md` (đã triển khai và bật ở commit `026f81a`).
- Các khẳng định từ bản audit trước (`*_citations.csv` trong `DATA_GUIDE.md`, gói Free trong `BUSINESS.md`, `evals/cases.yaml` trong `PROMPTS.md`, từ cảm tính/emoji) vẫn giữ trạng thái đã loại bỏ hoặc gắn nhãn `[Lỗi thời]`.

## 4. Lỗi và điểm bất thường phát hiện trong code (không sửa)

1. **Đệm khoảng trắng trong `RedditAdapter` vẫn gây lỗi `422`:** `extension/src/features/analysis/content/adapters/reddit-adapter.ts:219-220` dùng `padEnd(20, ' ')` khi bài viết ngắn hơn 20 ký tự, nhưng backend (`backend/app/schemas/request.py:30`) kiểm tra `len(v.strip()) >= 20`.
2. **`vite.config.ts` không đọc `extension/.env` cho `manifest.json`:** `extension/vite.config.ts:5` dùng `process.env.VITE_BACKEND_URL` trực tiếp thay vì `loadEnv`, nên đổi URL trong `.env` không cập nhật `host_permissions` trong `dist/manifest.json`.
3. **11 lỗi Ruff đang tồn đọng ở `backend/`:** `ruff check .` báo lỗi `I001`, `F401`, `UP035`, `BLE001` tại `app/core/rate_limit.py`, `app/schemas/internal.py`, `app/services/__init__.py`, `app/services/base_service.py`, `tests/test_benchmark.py`, `tests/test_tavily_service.py` (sẽ làm trượt job `lint-and-typecheck` trên CI).
4. **CI bỏ sót `npm test` và che lỗi `test_e2e.py`:** `.github/workflows/ci.yml` không chạy `npm test` cho extension và chạy `pytest tests/test_e2e.py || echo "No test_e2e.py yet"`.
5. **Xử lý `Content-Length` trong `security_middleware`:** `backend/app/main.py:61` gọi `int(content_length)` không bắt `ValueError` (header lỗi định dạng gây `500`), và request `Transfer-Encoding: chunked` bỏ qua kiểm tra kích thước ở middleware.
6. **File dư không dùng:** `extension/setup_t3.cjs` (1 dòng `require` thừa) và `extension/src/features/analysis/content/ui/floating-button.css` (không được import; `floating-button.ts` dùng inline styles).
7. **Lệch tên miền nhỏ giữa backend và extension:** `backend/app/core/trusted_domains.json` dùng `cand.vn`, còn `extension/src/features/analysis/publisher-names.json` dùng `cand.com.vn` (và khai báo lặp khóa `"PLO.vn"` / `"plo.vn"`).
8. **Chưa pin phiên bản thư viện Python và chưa khai báo marker `e2e`:** `backend/requirements.txt` không pin version; `backend/tests/test_e2e.py:86` phát sinh `PytestUnknownMarkWarning` cho `@pytest.mark.e2e` và truyền trường thừa `domain` vào `Source(...)`.

## 5. Quyết định cần người

1. **Giấy phép và tuyên bố sử dụng:** Repo chưa có file `LICENSE` ở thư mục gốc trong khi `extension/package.json` ghi `"license": "ISC"`. Cần xác nhận giấy phép chung của dự án và có tạo file `LICENSE` hay không.
2. **Xoá hoặc gộp tài liệu:**
   - Đề xuất gộp phần đặc tả CSV của `scripts/DATA_GUIDE.md` vào `scripts/benchmark/README.md` và xoá `scripts/DATA_GUIDE.md`.
   - Xác nhận có giữ `backend/README.md`, `extension/README.md` làm runbook theo thư mục và giữ `BUSINESS.md` ở thư mục gốc hay chuyển vào `docs/`.
3. **Phạm vi sản phẩm và đối tượng người dùng ban đầu:** Phần thông tin bổ sung trước khi chạy chưa điền thay cho mẫu `[VÍ DỤ: ...]`. Cần nhóm xác nhận danh sách "Ngoài phạm vi" và "Đối tượng người dùng ban đầu" chính thức để chốt trong `ROADMAP.md` và `BUSINESS.md`.
4. **Commit 3 file code ở working tree và sửa 11 lỗi Ruff:** Tài liệu hiện phản ánh 3 file code đang sửa dở trong working tree (`trusted_domains.json`, `gemini_prompts.py`, `test_source_ranking.py`). Cần nhóm quyết định commit 3 file này và xử lý 11 lỗi Ruff để CI xanh.

## 6. Kết quả chạy thử lệnh

| Lệnh | Môi trường | Kết quả | Ghi chú |
|---|---|---|---|
| `cd extension && npm run lint` | Node v24.19.0 | Đạt (0 lỗi) | Chạy trực tiếp |
| `cd extension && npm run typecheck` | Node v24.19.0 | Đạt (0 lỗi) | Chạy trực tiếp |
| `cd extension && npm test` | Node v24.19.0 | Đạt (12/12 test pass) | Mock Chrome và `fetch` |
| `cd extension && npm run build` | Node v24.19.0 | Đạt (`dist/manifest.json` 1.19 kB) | Chạy trực tiếp |
| `cd backend && ruff check .` | Python 3.13.11 | Báo 11 lỗi lint | Không sửa code theo nguyên tắc |
| `cd backend && pytest --collect-only -q` | Python 3.13.11 | Thu thập 154 test | Xác nhận import và cấu trúc test hợp lệ |
| `cd backend && pytest tests/test_source_ranking.py -q` | Python 3.13.11 | Đạt (16/16 test pass) | Test đồng bộ chạy bình thường |
| `cd backend && pytest -m "not e2e"` và `pytest tests/test_e2e.py` | Python 3.13.11 (sandbox Windows) | Chưa chạy trọn vẹn trong phiên này | Test `asyncio`/`TestClient` từng bị treo trong sandbox Windows khi tạo loopback socketpair; cần chạy lại ngoài sandbox trên máy |
| `python scripts/benchmark/run_benchmark.py --help` | Python 3.13.11 | Đạt (exit 0) | Đã xác nhận tham số CLI |
| `python scripts/try_*.py`, `run_benchmark.py` (không `--cache-only`), `uvicorn`, `docker compose` | — | Không chạy thử | Gọi API thật tốn hạn mức hoặc khởi chạy dịch vụ daemon/Docker ngoài phạm vi kiểm tra |
