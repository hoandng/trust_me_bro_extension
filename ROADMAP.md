# ROADMAP.md

> Dự án: **Trust Me Bro** — Browser Extension kiểm chứng độ tin cậy nội dung mạng xã hội  
> Trạng thái hiện tại: **MVP hoàn chỉnh về lõi kỹ thuật & đo lường** (hỗ trợ Facebook + Reddit, bộ chọn & xoay vòng model Gemini, SQLite metrics/cache, benchmark 3 chế độ).  
> Tham chiếu định hướng kinh doanh tại [BUSINESS.md](BUSINESS.md), chi tiết kiến trúc tại [ARCHITECTURE.md](ARCHITECTURE.md) và yêu cầu bảo mật tại [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md).

---

## Milestone 1: MVP End-to-End trên Facebook

Mục tiêu: Chứng minh luồng kiểm chứng hoạt động từ trình duyệt tới AI backend.

- [x] Khung dự án: Chrome Extension Manifest V3 (Vite + TypeScript) + Backend FastAPI.
- [x] Content script: bắt vùng văn bản bôi đen (20–2000 ký tự) trên Facebook, hiển thị nút nổi trong Shadow DOM.
- [x] Background & Side Panel: truyền message nội bộ, gọi `POST /api/v1/analyze` và hiển thị kết luận, độ tin cậy, giải thích, danh sách nguồn.
- [x] Tích hợp 3 dịch vụ bên ngoài: Gemini API (Interactions API), Google Fact Check Tools API, Tavily Search API.
- [x] Orchestrator 3 giai đoạn: trích xuất khẳng định → tra cứu song song Fact Check & Tavily → đánh giá tổng hợp có trích dẫn nguồn.
- [x] Bảo mật cơ bản: giữ API key bên thứ ba ở `.env` backend, CORS theo `ALLOWED_ORIGINS`, giới hạn độ dài input và body size.

---

## Milestone 2: Ổn định, Trải nghiệm người dùng & Nền tảng đo lường

Mục tiêu: Hệ thống ổn định, chống lạm dụng chi phí, đo được chất lượng và chi phí thực tế.

- [x] Tái cấu trúc extension theo tính năng (`entrypoints/`, `features/analysis/`, `infrastructure/`, `shared/`) và bổ sung test mock (`npm test`).
- [x] Trạng thái rõ ràng theo từng tab (`idle`, `loading` 3 bước, `success`, `error`, `RETRY_ANALYSIS`) và dọn RAM/session khi đóng hoặc chuyển trang.
- [x] Rate limiting nhiều tầng ở backend (IP/phút, Key/ngày, Global/ngày) và xử lý IP tin cậy sau reverse proxy (`TRUST_PROXY_HEADERS`).
- [x] Trả trạng thái từng dịch vụ (`service_status`) khi nhà cung cấp tra cứu lỗi hoặc hết thời gian (`ANALYSIS_TIMEOUT_SECONDS=25`).
- [x] Bộ chọn model Gemini trên Side Panel (tải lười khi mở Cài đặt, lưu `chrome.storage.local`), tự xoay vòng model khi gặp `429` và trả `503` + `Retry-After` khi cạn quota toàn bộ model.
- [x] **A1 — Chuẩn hóa Fact Check:** Bảng rating tiếng Anh & tiếng Việt, khóa `original_stance`, chỉ cho phép nguồn Fact Check đầu tiên đổi verdict khi khớp đúng mệnh đề (`factcheck_match=true`).
- [x] **A2 — Bằng chứng & Thời gian:** Giới hạn tối đa 2 truy vấn song song kèm fallback, xếp hạng nguồn theo tier (`trusted_domains.json`), truyền ngày Việt Nam và `published_date` để phát hiện tin cũ đăng lại.
- [x] **A3 — Tài nguyên & Độ trễ:** Dùng chung `httpx.AsyncClient` và `genai.Client` qua lifespan, áp ngân sách monotonic và ghi log JSON thời gian từng bước (`extract_ms`, `evidence_ms`, `assess_ms`, `total_ms`).
- [x] **B1 — Số liệu & Thống kê:** Lưu metadata phân tích (SHA-256 NFKC, không lưu text/URL gốc) và phản hồi (`POST /api/v1/feedback`) vào SQLite `metrics.db`; cung cấp `GET /api/v1/stats/summary` cho admin.
- [x] **B2 — Benchmark 3 chế độ:** Hoàn thiện `scripts/benchmark/run_benchmark.py` so sánh `llm_only`, `llm_factcheck` và `full` kèm bộ dataset tiếng Việt 100 mẫu, resume cache và báo cáo Macro-F1 / McNemar / chi phí / độ trễ.
- [x] **C2 — Nâng cấp Side Panel UX:** Banner kết luận dễ hiểu, mức chắc chắn 3 vạch (không phần trăm), đánh dấu giải thích 3 trạng thái (`[[+...]]`, `[[-...]]`, `[[?...]]`), ánh xạ tên báo (`publisher-names.json`), ngày xuất bản, sao chép bản tóm tắt chia sẻ và khung UI đánh giá 5 sao (tạm tắt gửi mạng qua `FEEDBACK_ENDPOINT_ENABLED = false`).

---

## Milestone 3: Hoàn thiện sản phẩm & Đồng bộ dữ liệu (Ưu tiên P0/P1)

Mục tiêu: Giảm ma sát khi dùng trên News Feed, đồng bộ phản hồi người dùng và tăng độ chính xác tiếng Việt.

- [x] **C1 — Cache kết quả phân tích:** Bảng `analysis_cache` trong `metrics.db` theo hash nội dung chuẩn hóa, phiên bản prompt, model và ngôn ngữ; hỗ trợ TTL theo mức tin cậy, miễn hạn mức key/ngày khi hit cache và tham số `bypass_cache`.
- [ ] **Đồng bộ schema Feedback giữa Extension và Backend:** Thống nhất hợp đồng `/api/v1/feedback` (giữa `{request_id, rating, comment}` trên UI 5 sao của Side Panel và `{request_id, helpful, reason}` ở backend) rồi bật `FEEDBACK_ENDPOINT_ENABLED = true`.
- [ ] **Mở rộng nguồn tin cậy Việt Nam ở Backend:** Bổ sung danh sách báo chính thống và kênh kiểm chứng Việt Nam vào `backend/app/core/trusted_domains.json` (`tier1`/`tier2`/`display_names`) và tối ưu `TAVILY_INCLUDE_DOMAINS` / truy vấn tiếng Việt.
- [ ] **Kiểm chứng ngay trên News Feed & tự động bóc bài:** Mở rộng chèn nút kiểm chứng cho từng bài đăng ngay trên News Feed Facebook và Reddit (hiện mới hỗ trợ trang chi tiết `/comments/` trên Reddit), cho phép click kiểm chứng toàn bài không cần bôi đen.
- [ ] **Tóm tắt bài báo:** Tạo tính năng `features/article-summary/` và endpoint backend tương ứng (định hướng cho gói nâng cao).
- [ ] **Lịch sử phân tích cho người dùng:** Cho phép xem lại lịch sử kiểm chứng (yêu cầu thiết kế bổ sung cơ chế lưu trữ và quyền riêng tư tương ứng).

---

## Milestone 4: Mở rộng đa nền tảng & Nguồn kiểm chứng

- [x] Thiết kế `PlatformAdapter` + registry và triển khai `RedditAdapter` (bôi đen + nút bài viết `/comments/`).
- [ ] **Adapter cho X (Twitter):** Thêm `XAdapter` trong extension và cập nhật `matches`/`host_permissions` trong `extension/vite.config.ts` (backend `AnalyzeRequest.platform` đã hỗ trợ `"x"`).
- [ ] **Đa dạng hóa nguồn dữ liệu:** Tích hợp thêm nguồn fact-check / tri thức tiếng Việt và quốc tế ngoài Google Fact Check Tools API & Tavily.

---

## Milestone 5: Production-ready & Vận hành thương mại

- [ ] **Xác thực động:** Thay `VITE_EXTENSION_API_KEY` tĩnh trong extension bằng cơ chế đăng nhập / cấp token động (OAuth / JWT / Firebase Auth) để phân biệt người dùng và áp dụng hạn mức theo gói (Free / Pro / Team).
- [ ] **Kho trạng thái dùng chung:** Di chuyển rate limiter, model cooldown và cache từ bộ nhớ process / SQLite local sang kho phân tán (như Redis) để chạy nhiều worker/instance an toàn.
- [ ] **Giám sát chi phí & cảnh báo:** Xây dựng dashboard vận hành dựa trên `/api/v1/stats/summary` và đặt cảnh báo ngưỡng chi phí API Gemini/Tavily.
- [ ] **Phát hành chính thức:** Hoàn thiện Chính sách quyền riêng tư, Điều khoản sử dụng, thử nghiệm pilot với nhóm người dùng mục tiêu và phát hành lên Chrome Web Store.
