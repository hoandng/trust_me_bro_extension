# AGENT

Quy ước làm việc, lệnh kiểm tra, quy chuẩn mã nguồn và giới hạn phạm vi dành cho AI agent và người đóng góp trong repo TrustMeBro.

Cập nhật theo commit `f491d97`, 20/11/2026.

## Lệnh kiểm tra bắt buộc trước khi hoàn thành

Chạy đầy đủ các lệnh tương ứng với phần mã bị thay đổi:

```bash
# Backend (từ thư mục backend/, đã kích hoạt .venv)
ruff check .
pytest -m "not e2e"
pytest tests/test_e2e.py

# Extension (từ thư mục extension/)
npm run lint
npm run typecheck
npm test
npm run build
```

Pre-commit (`.pre-commit-config.yaml`) chạy `ruff --fix`, `ruff-format`, `gitleaks`, `eslint` và `tsc --noEmit`. CI (`.github/workflows/ci.yml`) chạy trên PR vào `main` với Node `20` và Python `3.13`; CI hiện chưa chạy `npm test` nên phải chạy `npm test` tại máy.

## Quy ước code

- Đặt tên `camelCase` cho TypeScript (`extension/`) và `snake_case` cho Python (`backend/`).
- Dùng tiếng Anh cho tên biến, hàm, lớp; dùng tiếng Việt cho comment giải thích nghiệp vụ và chuỗi giao diện người dùng.
- Dùng `import type` cho mọi import chỉ chứa kiểu trong TypeScript; đặt dữ liệu hợp đồng message tại `extension/src/shared/messages.ts` và dùng chung `SIDEPANEL_PATH` tại `extension/src/shared/config.ts`.
- Dựng DOM Side Panel bằng `document.createElement` và `.textContent`; không dùng `innerHTML` với dữ liệu từ backend hoặc trang web.
- Đặt mọi lời gọi HTTP/SDK tới nhà cung cấp ngoài trong `backend/app/services/`; các dịch vụ tra cứu kế thừa `BaseService` và bọc `@safe_execute`.
- Chỉ sửa trong phạm vi task được giao; không tự ý thêm dependency mới hoặc refactor ngoài phạm vi khi chưa có xác nhận.

## Cập nhật tài liệu (bắt buộc)

Mỗi thay đổi code kèm cập nhật tài liệu trong CÙNG commit.

1. Trước khi hoàn thành, xác định tài liệu bị ảnh hưởng theo bảng "Thay đổi → tài liệu".
2. Chỉ sửa tài liệu sở hữu thông tin đó. Nơi khác dùng link, không chép lại.
3. Mô tả trạng thái hiện tại. Không kể lịch sử, không ghi tính năng dự kiến như đã xong.
4. Chạy `python scripts/docs_sync.py --check` và kiểm tra liên kết.
5. Báo cáo cuối task nêu: tài liệu đã sửa; tài liệu đã xem xét nhưng không cần sửa (kèm lý do).

Không cần sửa tài liệu khi: sửa lỗi không đổi hành vi công khai, refactor nội bộ, thêm test.

## Quy tắc phụ thuộc

Tuân thủ ranh giới lớp `entrypoints/ → features/ → infrastructure/` ở extension và `api/ → orchestrator/ → services/` ở backend. Không lặp lại chi tiết kiến trúc tại đây; xem sơ đồ, cấu trúc thành phần, hợp đồng API và lưu trữ SQLite/RAM tại [ARCHITECTURE.md](ARCHITECTURE.md), cấu hình môi trường tại [README.md](README.md) và yêu cầu bảo mật tại [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md).

## Quy ước kiểm thử

- Mọi test tự động ở `backend/tests/` phải mock các dịch vụ ngoài (Gemini, Fact Check, Tavily) bằng `respx` hoặc `unittest.mock`; không gọi API thật trong `pytest`.
- Test extension (`npm test`) dùng `extension/tests/run-tests.mjs` biên dịch TypeScript qua Vite vào `.cache/tests/` và chạy `node --test` với mock Chrome API và `fetch`.
- Khi sửa pipeline, bảo mật, cache hoặc hợp đồng message, bổ sung test hồi quy tương ứng tại `backend/tests/` hoặc `extension/tests/analysis.test.ts`.
- Khi cần chạy thử dịch vụ thật bằng khóa trong `backend/.env`, dùng các script thủ công trong `scripts/` (`try_factcheck.py`, `try_tavily.py`, `try_gemini.py`) hoặc `scripts/benchmark/run_benchmark.py`.

## Không làm

- Không đọc, in, log hoặc commit file `.env`, API key, token hay file `backend/data/metrics.db`.
- Không đặt `GEMINI_API_KEY`, `TAVILY_API_KEY` hoặc `FACTCHECK_API_KEY` trong mã nguồn hay bundle `extension/`.
- Không ghi nguyên văn nội dung bài đăng hoặc `page_url` của người dùng vào log, `analysis_metrics` hoặc `chrome.storage`.
- Không gọi trực tiếp API bên thứ ba từ route FastAPI, bỏ qua `AnalysisOrchestrator`, hoặc gọi từ `content/` của extension.
- Không đẩy thay đổi trực tiếp lên nhánh `main` và không bỏ qua các bước lint/typecheck/test.

## Quy ước nhánh và commit

- Tạo nhánh làm việc riêng từ `main` và mở Pull Request vào `main` để CI kiểm tra.
- Dùng tiền tố Conventional Commits ngắn gọn: `feat`, `fix`, `refactor`, `test`, `docs`, `chore` kèm phạm vi tùy chọn (ví dụ `feat(backend): ...`, `fix(extension): ...`, `docs: ...`).
- Khi thay đổi hành vi API, cấu hình hoặc trạng thái tính năng, cập nhật tài liệu sở hữu tương ứng trong cùng commit ([ARCHITECTURE.md](ARCHITECTURE.md), [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md), [README.md](README.md), [ROADMAP.md](ROADMAP.md)).
