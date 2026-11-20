# DOC_AUDIT

Báo cáo kiểm kê tài liệu, ma trận mâu thuẫn, khẳng định đã xoá, lỗi mã nguồn ghi nhận (không sửa), quyết định cần người và kết quả chạy thử lệnh của repo TrustMeBro.

Cập nhật theo commit `f491d97`, 20/11/2026.

## 1. Kiểm kê tài liệu

| File | Mục đích | Commit / ngày trước sửa | Tình trạng trước đồng bộ | Xử lý |
|---|---|---|---|---|
| `README.md` | Tổng quan, cài đặt, cấu hình, lệnh chạy | `3cd90d3` (2026-11-19) | Thiếu dòng commit trên header | Cập nhật header theo commit `f491d97` (132 dòng) |
| `ARCHITECTURE.md` | Thành phần, API, pipeline, lưu trữ, phụ thuộc | `3cd90d3` (2026-11-19) | Lỗi thời sau `f491d97`: vẫn ghi `stage_cap = max(20.0, timeout*0.6)` và chưa phản ánh `_build_evidence_jobs()` dùng `tool_calls` | Cập nhật Stage 0/1/2 khớp `analysis_orchestrator.py` mới và header `f491d97` (160 dòng) |
| `SECURITY_CHECKLIST.md` | Mối đe doạ, biện pháp, rủi ro, xử lý lộ khoá | `3cd90d3` (2026-11-19) | Thiếu dòng commit trên header | Cập nhật header theo commit `f491d97` (51 dòng) |
| `ROADMAP.md` | Trạng thái hạng mục, kế hoạch, ngoài phạm vi | `3cd90d3` (2026-11-19) | Thiếu dòng commit trên header | Cập nhật header theo commit `f491d97` (45 dòng) |
| `AGENT.md` | Quy ước làm việc cho AI agent và người đóng góp | `3cd90d3` (2026-11-19) | Nhắc lệnh không tồn tại `python scripts/docs_sync.py --check` và thiếu dòng commit | Xoá khẳng định không tồn tại, cập nhật header `f491d97` (58 dòng) |
| `PROMPTS.md` | Thư viện prompt khởi tạo T0–T15 | `3cd90d3` (2026-11-19) | Thiếu dòng commit trên header | Cập nhật header theo commit `f491d97` (552 dòng) |
| `BUSINESS.md` | Bài toán kinh doanh, phân khúc, giả định KPI | `3cd90d3` (2026-11-19) | Thiếu dòng commit trên header | Cập nhật header theo commit `f491d97` (114 dòng) |
| `backend/README.md` | Hướng dẫn vận hành backend | `3cd90d3` (2026-11-19) | Ghi `stage_cap = max(20.0, ...)` đã bị bỏ ở `f491d97`; thiếu dòng commit | Cập nhật giới hạn `20s` và header `f491d97` (58 dòng) |
| `extension/README.md` | Hướng dẫn build/debug extension | `3cd90d3` (2026-11-19) | Thiếu dòng commit trên header | Cập nhật header theo commit `f491d97` (51 dòng) |
| `scripts/benchmark/README.md` | Hướng dẫn chạy benchmark 3 chế độ | `3cd90d3` (2026-11-19) | Thiếu dòng commit trên header | Cập nhật header theo commit `f491d97` (57 dòng) |
| `scripts/DATA_GUIDE.md` | Đặc tả định dạng CSV benchmark | `3cd90d3` (2026-11-19) | Cần đồng bộ dòng commit | Cập nhật header theo commit `f491d97` (44 dòng) |
| `docs/PROJECT_CHARTER.md` | Tài liệu môn học (Project Charter) | `b00372f` (2026-11-18) | Ngoài phạm vi đồng bộ tài liệu kỹ thuật | Không sửa |
| `docs/FINAL_REPORT.md` | Báo cáo cuối kỳ môn học | `b00372f` (2026-11-18) | Ngoài phạm vi đồng bộ tài liệu kỹ thuật | Không sửa |
| `docs/DOC_TODO.md` | Danh sách chỗ trống cho Charter & Final Report | `b00372f` (2026-11-18) | Thuộc nhóm báo cáo môn học | Không sửa |

## 2. Ma trận mâu thuẫn

| Thông tin | Nơi A nói | Nơi B nói | Sự thật theo code | Xử lý |
|---|---|---|---|---|
| Trần timeout Stage 0 và Stage 2 | `ARCHITECTURE.md`, `backend/README.md`: `stage_cap = max(20.0, ANALYSIS_TIMEOUT_SECONDS * 0.6)` | `f491d97` (`analysis_orchestrator.py:88, 263`) | Code hiện dùng `min(timing.deadline, timing.clock() + 20)` cố định `20s` | Sửa `ARCHITECTURE.md` và `backend/README.md` khớp code |
| Định tuyến tool ở Stage 0 và Stage 1 | `gemini_prompts.py` + `analysis_orchestrator.py:138-179`: yêu cầu gọi tool `search_google_factcheck` / `search_web_tavily` và đọc `extraction.tool_calls` | `gemini_service.py:89-99, 217-223`, `schemas/internal.py`: không có `tool_calls` và không truyền `tools` | `ClaimExtraction` chỉ có `main_claim`, `search_queries`, `detected_lang`, `is_checkable`; `AnalysisContext` chưa có `tavily_topic` | Mô tả thực tế ở `ARCHITECTURE.md` và ghi lỗi nghiêm trọng vào mục 4 dưới |
| Script kiểm tra tài liệu `scripts/docs_sync.py` | `AGENT.md` (từ `3cd90d3`): yêu cầu chạy `python scripts/docs_sync.py --check` | Không có file này trong repo | `scripts/` chỉ có `DATA_GUIDE.md`, `try_*.py` và `benchmark/` | Xoá khẳng định không tồn tại khỏi `AGENT.md` |
| Dòng commit ở đầu tài liệu | Các file `.md` chỉ ghi `Cập nhật: 19/11/2026.` | Yêu cầu định dạng tài liệu kỹ thuật | Commit hiện tại là `f491d97` (20/11/2026) | Đặt dòng `Cập nhật theo commit \`f491d97\`, 20/11/2026.` ở mọi file |
| Số test trong `test_source_ranking.py` | `DOC_AUDIT.md` trước: `16/16` pass, tổng `154` test | Commit `f491d97` (`HEAD`) | `test_source_ranking.py` ở `HEAD` có `13` test, tổng `backend/tests/` thu thập `151` test | Cập nhật số liệu kiểm chứng thực tế tại mục 6 |
| Giấy phép | `extension/package.json`: `"license": "ISC"` | Root repo: không có file `LICENSE` | Chưa có file `LICENSE` ở thư mục gốc | Ghi đúng thực tế ở `README.md`, chờ người quyết định |

## 3. Khẳng định đã xoá vì không kiểm chứng được

- Lệnh `python scripts/docs_sync.py --check` và mục "Cập nhật tài liệu (bắt buộc)" tham chiếu tới bảng "Thay đổi → tài liệu" trong `AGENT.md` (không tồn tại trong mã nguồn).
- Công thức `stage_cap = max(20.0, ANALYSIS_TIMEOUT_SECONDS * 0.6)` trong `ARCHITECTURE.md` và `backend/README.md` (đã bị hoàn tác về hằng số `20` giây trong commit `f491d97`).

## 4. Lỗi và điểm bất thường phát hiện trong code (không sửa)

1. **Lỗi runtime `AttributeError` trong `AnalysisOrchestrator._build_evidence_jobs()` (`f491d97`):** `backend/app/orchestrator/analysis_orchestrator.py:142` truy cập `extraction.tool_calls` trực tiếp (ngoài khối `try/except`), trong khi `ClaimExtraction` (`backend/app/services/gemini_service.py:89-99`) không có thuộc tính `tool_calls`. Khi chạy thực tế với `ClaimExtraction` sẽ phát sinh `AttributeError` (HTTP `500`).
2. **Prompt định tuyến tool lệch với `GeminiService`, `AnalysisContext` và `TavilySearchService` (`f491d97`):** `EXTRACT_CLAIMS_PROMPT` yêu cầu gọi `search_google_factcheck` và `search_web_tavily`, nhưng `GeminiService.extract_claims()` không truyền `tools` vào `interactions.create()`; đồng thời `analysis_orchestrator.py:168` truyền `tavily_topic=tool_topic` dù `AnalysisContext` (`backend/app/schemas/internal.py`) không có trường `tavily_topic` và `TavilySearchService.check()` vẫn lặp cứng `("news", "general")`.
3. **Đệm khoảng trắng trong `RedditAdapter` vẫn gây lỗi `422`:** `extension/src/features/analysis/content/adapters/reddit-adapter.ts:219-220` dùng `padEnd(20, ' ')` khi bài viết ngắn hơn 20 ký tự, nhưng backend (`backend/app/schemas/request.py:30`) kiểm tra `len(v.strip()) >= 20`.
4. **`vite.config.ts` không đọc `extension/.env` cho `manifest.json`:** `extension/vite.config.ts:5` dùng `process.env.VITE_BACKEND_URL` trực tiếp thay vì `loadEnv`, nên đổi URL trong `.env` không cập nhật `host_permissions` trong `dist/manifest.json`.
5. **11 lỗi Ruff đang tồn đọng ở `backend/`:** `ruff check .` báo lỗi `I001`, `F401`, `UP035`, `BLE001` tại `app/core/rate_limit.py`, `app/schemas/internal.py`, `app/services/__init__.py`, `app/services/base_service.py`, `tests/test_benchmark.py`, `tests/test_tavily_service.py` (làm trượt job `lint-and-typecheck` trên CI).
6. **CI bỏ sót `npm test` và che lỗi `test_e2e.py`:** `.github/workflows/ci.yml` không chạy `npm test` cho extension và chạy `pytest tests/test_e2e.py || echo "No test_e2e.py yet"`.
7. **Xử lý `Content-Length` trong `security_middleware`:** `backend/app/main.py:61` gọi `int(content_length)` không bắt `ValueError` (header lỗi định dạng gây `500`), và request `Transfer-Encoding: chunked` bỏ qua kiểm tra kích thước ở middleware.
8. **File dư không dùng và lệch tên miền nhỏ:** `extension/setup_t3.cjs` và `extension/src/features/analysis/content/ui/floating-button.css` không được sử dụng; `trusted_domains.json` dùng `cand.vn` còn `publisher-names.json` dùng `cand.com.vn` (và lặp khóa `"PLO.vn"`/`"plo.vn"`); `backend/requirements.txt` chưa pin phiên bản và `test_e2e.py` chưa đăng ký marker `e2e`.

## 5. Quyết định cần người

1. **Xử lý lỗi `extraction.tool_calls` trong commit `f491d97`:** Quyết định hoàn thiện schema `ClaimExtraction`/`AnalysisContext`/`GeminiService` cho tính năng tool routing hay hoàn tác `_build_evidence_jobs()` về đọc `search_queries`.
2. **Giấy phép và tuyên bố sử dụng:** Repo chưa có file `LICENSE` ở thư mục gốc trong khi `extension/package.json` ghi `"license": "ISC"`. Cần xác nhận giấy phép chung của dự án và có tạo file `LICENSE` hay không.
3. **Xoá hoặc gộp tài liệu:** Đề xuất gộp phần đặc tả CSV của `scripts/DATA_GUIDE.md` vào `scripts/benchmark/README.md` và xoá `scripts/DATA_GUIDE.md`; xác nhận giữ hay gộp `backend/README.md`, `extension/README.md`, `BUSINESS.md`.
4. **Phạm vi sản phẩm và đối tượng người dùng ban đầu:** Phần thông tin bổ sung trước khi chạy chưa điền thay cho mẫu `[VÍ DỤ: ...]`. Cần nhóm xác nhận danh sách "Ngoài phạm vi" và "Đối tượng người dùng ban đầu" chính thức để chốt trong `ROADMAP.md` và `BUSINESS.md`.
5. **Sửa 11 lỗi Ruff và đồng bộ `docs/` môn học:** Quyết định dọn 11 lỗi Ruff để CI xanh và cập nhật các số liệu/mô tả lệch trong `docs/PROJECT_CHARTER.md`, `docs/FINAL_REPORT.md`.

## 6. Kết quả chạy thử lệnh

| Lệnh | Môi trường | Kết quả | Ghi chú |
|---|---|---|---|
| `cd extension && npm run lint` | Node v24.19.0 | Đạt (0 lỗi) | Chạy trực tiếp |
| `cd extension && npm run typecheck` | Node v24.19.0 | Đạt (0 lỗi) | Chạy trực tiếp |
| `cd extension && npm test` | Node v24.19.0 | Đạt (12/12 test pass) | Mock Chrome và `fetch` |
| `cd extension && npm run build` | Node v24.19.0 | Đạt (`dist/manifest.json` 1.19 kB) | Chạy trực tiếp |
| `cd backend && ruff check .` | Python 3.13.11 | Báo 11 lỗi lint | Không sửa code theo nguyên tắc |
| `cd backend && pytest --collect-only -q` | Python 3.13.11 | Thu thập 151 test | Xác nhận import và cấu trúc test hợp lệ |
| `cd backend && pytest tests/test_source_ranking.py -q` | Python 3.13.11 | Đạt (13/13 test pass) | Test đồng bộ chạy bình thường |
| `cd backend && pytest -m "not e2e"` và `pytest tests/test_e2e.py` | Python 3.13.11 (sandbox Windows) | Chưa chạy trọn vẹn trong phiên này | Test `asyncio`/`TestClient` bị treo trong sandbox Windows khi tạo loopback socketpair; cần chạy lại ngoài sandbox trên máy |
| `python scripts/benchmark/run_benchmark.py --help` | Python 3.13.11 | Đạt (exit 0) | Xác nhận tham số CLI |
| `python scripts/try_*.py`, `run_benchmark.py` (không `--cache-only`), `uvicorn`, `docker compose` | — | Không chạy thử | Gọi API thật tốn hạn mức hoặc khởi chạy dịch vụ daemon/Docker ngoài phạm vi kiểm tra |
