# ROADMAP

Tài liệu theo dõi trạng thái hiện tại theo hạng mục, kế hoạch tiếp theo và phạm vi loại trừ của TrustMeBro.

Cập nhật theo commit `f491d97`, 20/11/2026.

## Tổng quan trạng thái

| Hạng mục | Trạng thái | Căn cứ |
|---|---|---|
| Kiểm chứng đoạn văn bôi đen (Facebook, Reddit) và nút bài viết Reddit (`/comments/`) | Đã làm | `extension/src/features/analysis/content/`, `extension/tests/analysis.test.ts` |
| Pipeline 3 giai đoạn (Gemini, Fact Check, Tavily) kèm xoay vòng model | Đã làm | `backend/app/orchestrator/analysis_orchestrator.py`, `backend/app/services/`, `backend/tests/` |
| Xếp hạng nguồn tin cậy quốc tế và Việt Nam (32 tên miền) | Đã làm | `backend/app/core/trusted_domains.json`, `backend/app/core/source_ranking.py`, `backend/tests/test_source_ranking.py` |
| Cache kết quả, lưu số liệu vận hành và thống kê admin (SQLite) | Đã làm | `backend/app/core/analysis_cache.py`, `backend/app/core/metrics.py`, `backend/app/api/v1/metrics.py` |
| Gửi đánh giá 5 sao kèm nhận xét từ Side Panel lên backend | Đã làm | `backend/app/api/v1/metrics.py`, `extension/src/shared/config.ts`, `backend/tests/test_metrics.py`, `extension/tests/analysis.test.ts` |
| Bảo mật nền tảng (auth, rate limit, proxy IP, chống XSS/prompt injection, CI) | Đã làm | `backend/app/api/deps.py`, `backend/app/main.py`, `.github/workflows/ci.yml` |
| Bộ benchmark 3 chế độ (`llm_only`, `llm_factcheck`, `full`) | Đã làm | `scripts/benchmark/run_benchmark.py`, `backend/tests/test_benchmark.py` |
| Nút kiểm chứng ngay trên News Feed Facebook và Reddit | Dự kiến | Chưa có adapter bóc bài ở News Feed (`facebook-adapter.ts`, `reddit-adapter.ts`) |
| Adapter trình duyệt cho X (Twitter) | Dự kiến | Backend `request.py` đã nhận `"x"`; extension chưa có `XAdapter` và `host_permissions` |
| Tóm tắt bài báo (`features/article-summary/`) | Dự kiến | Chưa có mã nguồn ở extension và backend |
| Lịch sử phân tích cho người dùng cuối | Dự kiến | Chưa có giao diện và lưu trữ lịch sử theo người dùng |
| Xác thực động (OAuth/JWT) và kho trạng thái dùng chung (Redis) | Dự kiến | Hiện dùng `VITE_EXTENSION_API_KEY` tĩnh và RAM/SQLite cục bộ |
| Dashboard chi phí, cảnh báo ngưỡng và phát hành Chrome Web Store | Dự kiến | Hiện mới có endpoint `GET /api/v1/stats/summary` |
| Đa dạng hóa nguồn kiểm chứng ngoài Google Fact Check và Tavily | Dự kiến | Chưa có `BaseService` bổ sung trong `backend/app/services/` |
| Nền tảng ngoài extension desktop Chromium hoặc đầu vào phi văn bản | Ngoài phạm vi | Phạm vi mã nguồn hiện tại là extension desktop xử lý văn bản trên Facebook/Reddit (cần nhóm xác nhận tại [DOC_AUDIT.md](docs/DOC_AUDIT.md)) |

## Đã hoàn thành

- Khung Chrome Extension Manifest V3 (Vite, TypeScript `strict`) và backend FastAPI kèm `Dockerfile` / `docker-compose.yml`.
- Chọn văn bản 20–2000 ký tự trên Facebook/Reddit với nút nổi trong closed Shadow DOM và nút kiểm chứng bài viết trên `/comments/` Reddit.
- Side Panel theo từng tab: 4 trạng thái, mức chắc chắn 3 vạch, đánh dấu giải thích `✓`/`✗`/`?`, nguồn kèm thái độ, sao chép tóm tắt, chọn model Gemini tải lười và gửi đánh giá 5 sao kèm nhận xét.
- Pipeline `AnalysisOrchestrator` với deadline đơn điệu, chuẩn hóa rating Fact Check EN/VI, ưu tiên FactCheck khớp mệnh đề, xếp hạng 32 tên miền (`trusted_domains.json`) và xoay vòng model khi `429`.
- SQLite `metrics.db` (`analysis_metrics`, `feedback`, `analysis_cache`) cùng bộ benchmark 3 chế độ và bộ test mock cho backend/extension.

## Kế hoạch tiếp theo

- **Nút kiểm chứng trên News Feed Facebook và Reddit:** Bóc tách nội dung bài đăng ngay tại trang chủ để kiểm chứng không cần bôi đen.
- **Adapter cho X (Twitter):** Bổ sung `XAdapter` và quyền host để mở rộng sang nền tảng X mà backend đã hỗ trợ trong schema.
- **Tóm tắt bài báo:** Bổ sung luồng tóm tắt nội dung bài báo dài cho người dùng cần nắm nhanh thông tin.
- **Lịch sử phân tích cho người dùng:** Cho phép xem lại các lượt kiểm chứng trước kèm cơ chế bảo vệ quyền riêng tư.
- **Đa dạng hóa nguồn kiểm chứng:** Tích hợp thêm nguồn đối chứng tiếng Việt và quốc tế ngoài Google Fact Check và Tavily.
- **Xác thực động và kho trạng thái phân tán:** Thay `VITE_EXTENSION_API_KEY` tĩnh bằng OAuth/JWT và đưa rate limit, cooldown, cache sang kho dùng chung để chạy nhiều worker.
- **Giám sát chi phí và phát hành Chrome Web Store:** Dựng dashboard theo dõi `/api/v1/stats/summary`, đặt cảnh báo chi phí và hoàn thiện tài liệu phát hành.

Chi tiết kiến trúc xem [ARCHITECTURE.md](ARCHITECTURE.md), bảo mật xem [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md), bài toán kinh doanh xem [BUSINESS.md](BUSINESS.md).
