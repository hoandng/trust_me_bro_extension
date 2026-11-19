# DOC_AUDIT

Báo cáo kiểm kê tài liệu, ma trận mâu thuẫn, khẳng định đã xoá, lỗi mã nguồn ghi nhận (không sửa), quyết định cần người và kết quả chạy thử lệnh của repo TrustMeBro.

Cập nhật theo commit `b00372f`, 19/11/2026 (đối chiếu cả 4 file mã nguồn đang có thay đổi ở working tree: `backend/app/core/trusted_domains.json`, `backend/app/orchestrator/analysis_orchestrator.py`, `backend/app/prompts/gemini_prompts.py`, `backend/tests/test_source_ranking.py`).

## 1. Kiểm kê tài liệu

| File | Mục đích | Commit / ngày trước sửa | Tình trạng trước đồng bộ | Xử lý |
|---|---|---|---|---|
| `README.md` | Tổng quan, cài đặt, cấu hình, lệnh chạy | `c4a41be` (2026-11-18) | Thiếu bảng biến môi trường đầy đủ và mục giấy phép; lặp mô tả pipeline; phiên bản Python/Node chưa thống nhất | Viết lại theo quyền sở hữu (≤ 150 dòng) |
| `ARCHITECTURE.md` | Thành phần, API, pipeline, lưu trữ, phụ thuộc | `c4a41be` (2026-11-18) | Lệch số lượng tên miền `trusted_domains.json` (ghi 4, thực tế 32) và `stage_cap` (ghi 20s cố định, thực tế `max(20.0, timeout*0.6)`); vượt 250 dòng (274 dòng); sơ đồ ASCII thay vì Mermaid | Viết lại với Mermaid và số liệu đúng code (≤ 250 dòng) |
| `SECURITY_CHECKLIST.md` | Mối đe doạ, biện pháp, rủi ro, xử lý lộ khoá | `c4a41be` (2026-11-18) | Thiếu mục "Khi lộ khoá", chưa tách rõ bảng dữ liệu gửi bên thứ ba / dữ liệu lưu và mục "Chưa có" | Viết lại theo mẫu bảng mối đe doạ + luồng dữ liệu + khi lộ khoá (≤ 100 dòng) |
| `ROADMAP.md` | Trạng thái hạng mục, kế hoạch, ngoài phạm vi | `c4a41be` (2026-11-18) | Vẫn liệt kê nguồn tin cậy Việt Nam là chưa làm; trình bày theo lịch sử Milestone 1–5 | Viết lại thành bảng 4 trạng thái và danh sách gọn (≤ 80 dòng) |
| `AGENT.md` | Quy ước làm việc cho AI agent và người đóng góp | `713879e` (2026-11-11) | Lỗi thời: bỏ sót SQLite `metrics.db`, `analysis_cache`, `metrics.py`, `source_ranking.py`; lặp cây thư mục; trỏ sai mục bảo mật của `ARCHITECTURE.md` | Viết lại khớp thực tế, trỏ link kiến trúc (≤ 100 dòng) |
| `PROMPTS.md` | Thư viện prompt khởi tạo T0–T15 | `d3ec857` (2026-11-10) | Hợp đồng API cũ (thiếu `bypass_cache`, `request_id`, `/feedback`, `/stats/summary`); thiếu nhãn trạng thái T0–T15; có emoji | Giữ nguyên nội dung prompt; đánh dấu trạng thái; thay hợp đồng bằng link |
| `BUSINESS.md` | Bài toán kinh doanh, phân khúc, giả định KPI | `37a39f1` (2026-11-10) | Sai số lượt gọi Tavily, sai thư mục `eval/`, sai nhãn UI stance, sai nguồn tính chi phí, ghi benchmark/cache chưa làm | Sửa toàn bộ khẳng định kỹ thuật lệch code; giữ nhãn `[GIẢ ĐỊNH]` |
| `backend/README.md` | Hướng dẫn vận hành backend | `bd421b6` (2026-11-11) | Lặp bảng env (và thiếu `SEARCH_QUERY_LIMIT`), lặp danh sách API, link chết `#23-luồng-xử-lý-tại-orchestrator`, ghi `stage_cap` cố định 20s | Rút gọn thành runbook backend; trỏ link về `README.md` và `ARCHITECTURE.md` |
| `extension/README.md` | Hướng dẫn build/debug extension | `d3ec857` (2026-11-10) | Ghi sai `chrome.storage.session` lưu đủ state; thiếu `handle-feedback.ts`, `explanation-parser.ts`, `share-summary.ts`, `source-url.ts`; lặp kiến trúc | Rút gọn thành runbook extension; trỏ link về `README.md` và `ARCHITECTURE.md` |
| `scripts/benchmark/README.md` | Hướng dẫn chạy benchmark 3 chế độ | `a1c994e` (2026-11-18) | Khớp phần lớn `run_benchmark.py`; thiếu dòng commit và liên kết tới `DATA_GUIDE.md` | Đồng bộ cờ CLI, đầu ra và thêm dòng commit |
| `scripts/DATA_GUIDE.md` | Đặc tả định dạng CSV benchmark | `dc68cdc` (2026-11-11) | Chứa log hội thoại AI, ngôi thứ nhất, link tuyệt đối `file:///f:/...`, ghi `dataset.csv` chỉ có 10 mẫu `example.invalid` và sinh `*_citations.csv` | Viết lại đúng `load_dataset()`/`load_annotations()` và đề xuất gộp/xoá |
| `docs/PROJECT_CHARTER.md` | Tài liệu môn học (Project Charter) | `b00372f` (2026-11-18) | Ngoài phạm vi đồng bộ tài liệu kỹ thuật | Không sửa |
| `docs/FINAL_REPORT.md` | Báo cáo cuối kỳ môn học | `b00372f` (2026-11-18) | Ngoài phạm vi đồng bộ tài liệu kỹ thuật | Không sửa |
| `docs/DOC_TODO.md` | Danh sách chỗ trống cho Charter & Final Report | `b00372f` (2026-11-18) | Ghi `trusted_domains.json` mới có 4 domain (lệch working tree) nhưng thuộc nhóm báo cáo môn học | Không sửa |

## 2. Ma trận mâu thuẫn

| Thông tin | Nơi A nói | Nơi B nói | Sự thật theo code | Xử lý |
|---|---|---|---|---|
| Số tên miền trong `trusted_domains.json` | `ARCHITECTURE.md`, `ROADMAP.md`: chỉ có 4 tên miền quốc tế, chưa có báo Việt Nam | `extension/src/features/analysis/publisher-names.json`: có sẵn báo Việt Nam | `backend/app/core/trusted_domains.json` có 32 tên miền (17 `tier1`, 15 `tier2`, 32 `display_names`, gồm 28 tên miền Việt Nam) | Cập nhật `ARCHITECTURE.md`, `ROADMAP.md`, `BUSINESS.md` |
| Trần thời gian Stage 0 & Stage 2 | `ARCHITECTURE.md`, `backend/README.md`: cố định `20s` | — | `analysis_orchestrator.py:84`: `stage_cap = max(20.0, settings.analysis_timeout_seconds * 0.6)` | Cập nhật `ARCHITECTURE.md`, `backend/README.md` |
| Lưu trữ backend | `AGENT.md`: chỉ có in-memory rate limit & cooldown | `README.md`, `ARCHITECTURE.md`: có SQLite `metrics.db` | `main.py`, `metrics.py`, `analysis_cache.py`: SQLite `backend/data/metrics.db` (3 bảng) + RAM `RateLimiter`/`GeminiModelPool` | Cập nhật `AGENT.md`, giữ chi tiết ở `ARCHITECTURE.md` |
| Nội dung `chrome.storage.session` | `extension/README.md`, `PROMPTS.md` (T4): lưu toàn bộ request/state | `ARCHITECTURE.md`, `SECURITY_CHECKLIST.md`: chỉ lưu `{status, request_id}` | `handle-analysis.ts`, `state-store.ts`: state đầy đủ chỉ giữ ở RAM `tabRuns`; session chỉ lưu `{status, request_id?}` và `geminiModelCatalog` | Cập nhật `extension/README.md`, giữ chi tiết ở `ARCHITECTURE.md` |
| Side Panel gọi API trực tiếp | `extension/README.md` dòng 78: mã gọi backend chỉ ở background | `extension/README.md` dòng 140: Side Panel tải `/api/v1/models` | `sidepanel/controller.ts:78` gọi trực tiếp `GET /api/v1/models` khi mở Cài đặt | Sửa nhất quán ở `ARCHITECTURE.md` và `extension/README.md` |
| Biến môi trường `SEARCH_QUERY_LIMIT` | `backend/README.md`: liệt kê 25 biến, thiếu `SEARCH_QUERY_LIMIT` | `backend/.env.example`: có `SEARCH_QUERY_LIMIT=2` | `backend/app/core/config.py:37`: `search_query_limit: int = Field(default=2, ge=1, le=2)` (tổng 26 biến) | Đưa đủ 26 biến backend + 2 biến extension vào `README.md` |
| Phiên bản Python & Node | `README.md`, `AGENT.md`, `backend/README.md`: Python `3.11+`; CI: Node `20`, Python `3.13` | `backend/Dockerfile`: `python:3.12-slim`; `docker-compose.yml`: `node:22-alpine`; `run-tests.mjs`: `node22` | `package-lock.json` yêu cầu Node `^20.19.0 \|\| ^22.13.0 \|\| >=24`; code Python dùng cú pháp 3.11+ | Thống nhất khai báo ở `README.md` (Python `3.12+`, Node `22.13+` / tương thích `20.19+`, `24+`) và ghi chú khác biệt CI/Docker |
| Hợp đồng API trong `PROMPTS.md` | `PROMPTS.md`: thiếu `bypass_cache`, `request_id`, `/feedback`, `/stats/summary` | `ARCHITECTURE.md`, `backend/README.md`: có đủ 5 endpoint | `request.py`, `response.py`, `analyze.py`, `metrics.py` có đủ 5 endpoint và các trường trên | Thay khối hợp đồng lặp trong `PROMPTS.md` bằng link tới `ARCHITECTURE.md` |
| Cấu trúc dataset và đầu ra benchmark | `scripts/DATA_GUIDE.md`: `dataset.csv` 10 mẫu `example.invalid`, bắt buộc `source_url`, xuất `*_citations.csv` | `scripts/benchmark/README.md`: 100 mẫu VN, xuất 4 file (`report.md`, `raw.csv`, `chart.png`, `summary.json`) | `run_benchmark.py` không đọc `source_url`, không sinh `*_citations.csv`; `dataset.csv` có 71 mẫu, `dataset_vn_benchmark_100.csv` có 100 mẫu | Viết lại `scripts/DATA_GUIDE.md` khớp code |
| Số lượt gọi Tavily & nhãn UI trong `BUSINESS.md` | `BUSINESS.md`: 1 lượt Tavily, thư mục `eval/`, nhãn `Ủng hộ / Bác bỏ / Trung lập`, đo chi phí từ log `model_usage` | `ARCHITECTURE.md`, `map-response.ts`, `metrics.py` | Tối đa 4 lượt Tavily (2 query × 2 topic); thư mục `scripts/benchmark/`; nhãn UI `Ủng hộ / Phản bác / Liên quan`; chi phí tính ở `metrics.py` SQLite | Cập nhật `BUSINESS.md` khớp mã nguồn |
| Liên kết nội bộ chết | `backend/README.md`: `../ARCHITECTURE.md#23-luồng-xử-lý-tại-orchestrator`; `AGENT.md`: "mục 3 bảo mật của ARCHITECTURE.md"; `DATA_GUIDE.md`: `file:///f:/...` | — | Các anchor và đường dẫn tuyệt đối không tồn tại hoặc không hợp lệ | Thay bằng đường dẫn tương đối hợp lệ |
| Giấy phép | `extension/package.json`: `"license": "ISC"` | Root repo: không có file `LICENSE`; `README.md`: không nhắc giấy phép | Không có file `LICENSE` ở gốc repo | Ghi đúng thực tế ở `README.md`, đưa vào mục Quyết định cần người |

## 3. Khẳng định đã xoá vì không kiểm chứng được

- Câu khẳng định trong `scripts/DATA_GUIDE.md` rằng benchmark tạo file `benchmark_<ngày>_citations.csv` với cột `supports_verdict` (không tồn tại trong `scripts/benchmark/run_benchmark.py`).
- Câu khẳng định trong `scripts/DATA_GUIDE.md` rằng `dataset.csv` chỉ có 10 mẫu với `example.invalid` và cột `source_url` là bắt buộc.
- Câu khẳng định trong `BUSINESS.md` rằng gói Free 10 lượt/ngày đã có sẵn hạ tầng phân theo người dùng (code chỉ giới hạn 100 lượt/24h trên một static key dùng chung) và chi phí đo từ log `model_usage`.
- Câu khẳng định trong `PROMPTS.md` về tag `v0.1.0-alpha` và đường dẫn `backend/evals/cases.yaml`, `scripts/run_evals.py` (không tồn tại trong repo; giữ nguyên thân prompt T14 nhưng gắn nhãn `[Lỗi thời]`).
- Câu khẳng định trong `extension/README.md` rằng "Chưa có cache trong source hiện tại" mà không phân biệt client/server (backend đã có `AnalysisCache`).
- Các từ cảm tính / so sánh không có số đo ("mạnh mẽ", "linh hoạt", "tối ưu", "trực quan", "dễ hiểu", "nhanh hơn", "rõ rệt") và toàn bộ emoji, ngôi thứ nhất trong các file đã cập nhật.

## 4. Lỗi và điểm bất thường phát hiện trong code (không sửa)

1. **Lệch schema `/api/v1/feedback`:** Backend (`backend/app/api/v1/metrics.py:11-18`) yêu cầu `{request_id, helpful, reason?}` với `extra="forbid"`, trong khi extension (`extension/src/features/analysis/background/handle-feedback.ts:27-31`) gửi `{request_id, rating, comment?}`. Hiện được chặn bằng `FEEDBACK_ENDPOINT_ENABLED = false` (`extension/src/shared/config.ts:5`).
2. **Đệm khoảng trắng trong `RedditAdapter` vẫn gây lỗi `422`:** `extension/src/features/analysis/content/adapters/reddit-adapter.ts:219-220` dùng `padEnd(20, ' ')` khi bài viết ngắn hơn 20 ký tự, nhưng backend (`backend/app/schemas/request.py:30`) kiểm tra `len(v.strip()) >= 20`.
3. **`vite.config.ts` không đọc `extension/.env` cho `manifest.json`:** `extension/vite.config.ts:5` dùng `process.env.VITE_BACKEND_URL` trực tiếp thay vì `loadEnv`, nên đổi URL trong `.env` không cập nhật `host_permissions` trong `dist/manifest.json`.
4. **11 lỗi Ruff đang tồn đọng ở `backend/`:** `ruff check .` báo lỗi `I001`, `F401`, `UP035`, `BLE001` tại `app/core/rate_limit.py`, `app/schemas/internal.py`, `app/services/__init__.py`, `app/services/base_service.py`, `tests/test_benchmark.py`, `tests/test_tavily_service.py` (sẽ làm trượt job `lint-and-typecheck` trên CI).
5. **CI bỏ sót `npm test` và che lỗi `test_e2e.py`:** `.github/workflows/ci.yml` không chạy `npm test` cho extension và chạy `pytest tests/test_e2e.py || echo "No test_e2e.py yet"`.
6. **Xử lý `Content-Length` trong `security_middleware`:** `backend/app/main.py:60` gọi `int(content_length)` không bắt `ValueError` (header lỗi định dạng gây `500`), và request `Transfer-Encoding: chunked` bỏ qua kiểm tra kích thước ở middleware.
7. **File dư không dùng:** `extension/setup_t3.cjs` (1 dòng `require` thừa) và `extension/src/features/analysis/content/ui/floating-button.css` (không được import; `floating-button.ts` dùng inline styles).
8. **Lệch tên miền nhỏ giữa backend và extension:** `backend/app/core/trusted_domains.json` dùng `cand.vn`, còn `extension/src/features/analysis/publisher-names.json` dùng `cand.com.vn` (và khai báo lặp khóa `"PLO.vn"` / `"plo.vn"`).
9. **Chưa pin phiên bản thư viện Python và chưa khai báo marker `e2e`:** `backend/requirements.txt` không pin version; `backend/tests/test_e2e.py:86` phát sinh `PytestUnknownMarkWarning` cho `@pytest.mark.e2e` và truyền trường thừa `domain` vào `Source(...)`.

## 5. Quyết định cần người

1. **Giấy phép và tuyên bố sử dụng:** Repo chưa có file `LICENSE` ở thư mục gốc trong khi `extension/package.json` ghi `"license": "ISC"`. Cần xác nhận giấy phép chung của dự án và có tạo file `LICENSE` hay không.
2. **Xoá hoặc gộp tài liệu:**
   - Đề xuất gộp phần đặc tả CSV của `scripts/DATA_GUIDE.md` vào `scripts/benchmark/README.md` và xoá `scripts/DATA_GUIDE.md`.
   - Xác nhận có giữ `backend/README.md`, `extension/README.md` làm runbook theo thư mục và giữ `BUSINESS.md` ở thư mục gốc hay chuyển vào `docs/`.
3. **Phạm vi sản phẩm và đối tượng người dùng ban đầu:** Phần thông tin bổ sung trước khi chạy chưa điền thay cho mẫu `[VÍ DỤ: ...]`. Cần nhóm xác nhận danh sách "Ngoài phạm vi" và "Đối tượng người dùng ban đầu" chính thức để chốt trong `ROADMAP.md` và `BUSINESS.md`.
4. **Trạng thái tính năng làm một phần trong `ROADMAP.md`:** Tạm xếp gửi phản hồi từ Side Panel là `Đang làm` (đã có API backend và UI extension nhưng lệch schema, đang tắt cờ gửi mạng), còn adapter X và nút kiểm chứng News Feed là `Dự kiến`. Cần xác nhận cách phân loại này.
5. **Commit 4 file code ở working tree và sửa 11 lỗi Ruff:** Tài liệu hiện phản ánh 4 file code đang sửa dở trong working tree (ghi theo `HEAD` `b00372f`). Cần nhóm quyết định commit 4 file này và xử lý 11 lỗi Ruff để CI xanh.

## 6. Kết quả chạy thử lệnh

| Lệnh | Môi trường | Kết quả | Ghi chú |
|---|---|---|---|
| `cd extension && npm run lint` | Node v24.19.0 | Đạt (0 lỗi) | Chạy trực tiếp |
| `cd extension && npm run typecheck` | Node v24.19.0 | Đạt (0 lỗi) | Chạy trực tiếp |
| `cd extension && npm test` | Node v24.19.0 | Đạt (12/12 test pass) | Mock Chrome và `fetch` |
| `cd extension && npm run build` | Node v24.19.0 | Đạt (`dist/manifest.json` 1.19 kB) | Chạy trực tiếp |
| `cd backend && ruff check .` | Python 3.13.11 | Báo 11 lỗi lint | Không sửa code theo nguyên tắc |
| `cd backend && pytest --collect-only -q` | Python 3.13.11 | Thu thập 152 test | Xác nhận import và cấu trúc test hợp lệ |
| `cd backend && pytest tests/test_source_ranking.py -q` | Python 3.13.11 | Đạt (16/16 test pass) | Test đồng bộ chạy bình thường |
| `cd backend && pytest -m "not e2e"` và `pytest tests/test_e2e.py` | Python 3.13.11 (sandbox Windows) | Chưa hoàn tất trong sandbox | Các test `asyncio`/`TestClient` bị treo khi tạo loopback socketpair trong sandbox Windows; cần chạy trực tiếp ngoài sandbox trên máy |
| `python scripts/benchmark/run_benchmark.py --help` | Python 3.13.11 | Đạt (exit 0) | Xác nhận toàn bộ tham số CLI |
| `python scripts/try_*.py`, `run_benchmark.py` (không `--cache-only`), `uvicorn`, `docker compose` | — | Không chạy thử | Gọi API thật tốn hạn mức hoặc khởi chạy dịch vụ daemon/Docker ngoài phạm vi kiểm tra |
