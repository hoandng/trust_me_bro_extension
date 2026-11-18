# DOC_TODO.md

> Danh sách công việc nhóm cần hoàn tất trước hạn nộp **20/11/2026** để bỏ toàn bộ chỗ trống `**[CẦN ĐIỀN: ...]**` trong `docs/PROJECT_CHARTER.md` và `docs/FINAL_REPORT.md`.

---

## 1. Các chỗ còn trống cần người thật cung cấp

### (a) Số liệu cần đo & kiểm chứng (benchmark bổ sung, user test, chi phí)

1. **Chấm tay độ hợp lệ nguồn trích dẫn (`FINAL_REPORT.md` mục 7.3 & `PROJECT_CHARTER.md` mục 1.5):**
   - Hiện repo chưa có file chấm tay citation cho đợt chạy `dataset_vn_benchmark_100_17-11-2026_18-34-33` (`run_benchmark.py` v2 chưa tạo phiếu chấm citation).
   - Cần chọn ngẫu nhiên hoặc toàn bộ mẫu, chấm tỷ lệ nguồn thực sự ủng hộ kết luận / liên quan gián tiếp / không liên quan để điền vào mục 7.3 và mục tiêu ở Charter 1.5.
2. **Quy trình gán nhãn & độ đồng thuận (`FINAL_REPORT.md` mục 7.1):**
   - Mô tả ai chấm nhãn 100 mẫu trong `dataset_vn_benchmark_100.csv`, quy tắc gán nhãn, và chỉ số đồng thuận (ví dụ Cohen's kappa) nếu có chấm chéo.
3. **Thử nghiệm người dùng & Khảo sát (`FINAL_REPORT.md` mục 2.1, 2.5, 7.6, 9.2, Phụ lục D; `PROJECT_CHARTER.md` mục 1.2, 1.5):**
   - Quy mô `n` người dùng thử, đối tượng (persona thực tế), tỷ lệ đọc tin trên máy tính so với điện thoại, kết quả câu hỏi mức hữu ích (1–5), activation, số lượt kiểm chứng/tuần, quan sát giao diện và chỉnh sửa sau thử nghiệm.
4. **Đánh giá mô hình kinh doanh, mức sẵn lòng trả & gói API (`PROJECT_CHARTER.md` mục 2.3, 5; `FINAL_REPORT.md` mục 2.4):**
   - Xác định mức sẵn lòng trả tiền (từ khảo sát), đánh giá khả thi 3 hướng kinh doanh (Freemium, B2B2C, Tổ chức), khai báo gói API thực tế của nhóm (free tier / trả phí, quota, ngân sách) và nơi triển khai backend (`Render`/`Railway`/`cục bộ`, điền vào mục 5 Charter và mục 3.9 Final Report).
   - Nếu cấu hình đơn giá thật `GEMINI_TOKEN_PRICES` và `TAVILY_USD_PER_CREDIT` trong `.env`, đối chiếu lại chi phí thực tế so với mức `$0.01713/lượt` đang dùng đơn giá tham chiếu trong `run_benchmark.py`.
5. **Đối chiếu giải pháp thay thế / đối thủ (`PROJECT_CHARTER.md` mục 2.2; `FINAL_REPORT.md` mục 2.3):**
   - Xác minh trực tiếp tốc độ, độ chính xác và khả năng dẫn nguồn của các đối thủ thực tế (giao diện web ChatGPT/Gemini, Google Fact Check Explorer, trang kiểm chứng như Snopes/báo Việt Nam, Community Notes nếu bổ sung) kèm dẫn nguồn; không đánh đồng `llm_only` hay `llm_factcheck` qua API với trải nghiệm web UI của đối thủ mà không giải thích rõ.
6. **Xác nhận các mục đánh dấu `(cần người kiểm tra)`:**
   - Kiểm tra lại link repository (`https://github.com/hoandng/trust-me-bro-2.0`) và mốc thời gian thực hiện 5 giai đoạn trong `PROJECT_CHARTER.md` mục 6 (đang tổng hợp từ `git log`).
   - Chọn các công nghệ mà nhóm đánh giá là mới so với chương trình môn học ở `FINAL_REPORT.md` mục 5.
   - Bổ sung thảo luận đạo đức/trách nhiệm khi tin đúng bị gán nhãn sai ở `FINAL_REPORT.md` mục 8 và chính sách dữ liệu bên thứ ba (nếu cần).

### (b) Thông tin cá nhân, môn học và phân công

1. **Họ tên, MSSV, email** của các thành viên (`PROJECT_CHARTER.md` đầu trang & mục 4; `FINAL_REPORT.md` đầu trang & Phụ lục E).
2. **Tên môn học, họ tên giảng viên**, **ngày hoàn thành tài liệu** (`dd/11/2026`), **ngày bảo vệ theo lịch lớp**, và **đối tác/tổ chức tham gia nếu có** (`PROJECT_CHARTER.md` mục 6 & 8).
3. **Phân công công việc thực tế** của từng thành viên (`PROJECT_CHARTER.md` mục 4; `FINAL_REPORT.md` Phụ lục E).

### (c) Hình ảnh cần chụp màn hình

Chèn ảnh vào `FINAL_REPORT.md` mục **3.8** (giao diện) và mục **6.5** (hướng dẫn sử dụng), bảo đảm không lộ API key, token hay thông tin cá nhân:
1. Trang Facebook/Reddit có bôi đen đoạn văn và **nút nổi `FloatingButton`** hiển thị phía trên vùng chọn.
2. Trang chi tiết bài viết Reddit (`/comments/`) có viền nhận diện và nút **"Kiểm chứng bài viết"**.
3. Side Panel trạng thái **Đang tải (`loading`)** với 3 bước tiến trình.
4. Side Panel kết quả **`likely_true` ("Có vẻ đúng")** kèm giải thích có đánh dấu inline `✓`/`✗`/`?`, mức chắc chắn 3 vạch và danh sách nguồn.
5. Side Panel kết quả **`likely_false` ("Có vẻ sai sự thật")**.
6. Side Panel kết quả **`mixed` ("Đúng một phần")**.
7. Side Panel kết quả **`unverified` ("Chưa đủ bằng chứng")** kèm câu cảnh báo `"Đừng vội chia sẻ tin này."`.
8. Side Panel trạng thái **Lỗi (`error`)** kèm nút **"Thử lại"**.
9. Side Panel khi mở mục **Cài đặt chọn model Gemini** (`#settings-panel`) và mục **Chi tiết kỹ thuật** (`#tech-details`) gập/mở.

### (d) Tài liệu tham khảo cần tìm (`FINAL_REPORT.md` mục Tài liệu tham khảo & `PROJECT_CHARTER.md` mục 1.1)

1. **Số liệu thị trường & bối cảnh tin giả tại Việt Nam** (2–3 số liệu kèm báo cáo/nguồn và năm xuất bản cho Charter 1.1 và Final Report 1.1).
2. **URL tài liệu chính thức** cho:
   - Google Fact Check Tools API
   - Tavily Search API
   - Chrome Extensions (Manifest V3, Side Panel API)
3. **Nguồn trích dẫn đối thủ & bài kiểm chứng tham chiếu ngoài dataset** (nếu bổ sung vào mục 2.2/2.3).

---

## 2. Chỗ tài liệu nháp mâu thuẫn với code và cách đã sửa

| Vị trí trong bản nháp | Mâu thuẫn với mã nguồn | Cách đã sửa |
|---|---|---|
| `FINAL_REPORT.md` mục 3.3 (dòng 180) | Bản nháp ghi *"side panel chỉ hiển thị, không gọi mạng trực tiếp"*. Thực tế `extension/src/features/analysis/sidepanel/controller.ts` gọi trực tiếp `getFromBackend('/api/v1/models')` khi người dùng mở mục Cài đặt lần đầu và cache vào `chrome.storage.session`. | Đã cập nhật lại mô tả và sơ đồ Mermaid mục 3.3 thể hiện Side Panel gọi lười `GET /api/v1/models`. |
| `FINAL_REPORT.md` mục 3.5 (sequence diagram) | Bản nháp vẽ `BG-->>CS: Kết quả` rồi `CS->>U: Hiển thị side panel`. Thực tế Content Script không nhận kết quả; `handle-analysis.ts` mở trực tiếp Side Panel (`chrome.sidePanel.open`), lưu `{status, request_id}` vào `chrome.storage.session`, rồi Side Panel tự lấy chi tiết qua `GET_ANALYSIS_STATE`. Sơ đồ cũng thiếu nhánh cache hit (`analysis_cache`) và nhánh dừng khi rỗng nguồn/timeout. | Đã vẽ lại `sequenceDiagram` với các participant thật (`U`, `CS`, `BG`, `SP`, `API`, `ORC`, `G`, `FC`, `TV`), bổ sung nhánh cache hit, dừng sớm không có nguồn và cập nhật Side Panel. |
| `FINAL_REPORT.md` mục 3.3 (dòng 164) & 3.4 | Đánh dấu `[CẦN ĐIỀN]` ở thành phần SQLite và chỉ nhắc `metrics` (thiếu `analysis_cache` và `feedback`). | Đã xác nhận đã triển khai `backend/data/metrics.db` với 3 bảng (`analysis_metrics`, `feedback`, `analysis_cache`) tại `metrics.py` và `analysis_cache.py`. |
| `FINAL_REPORT.md` mục 3.1 (FR-10) & 3.8 (mục 7) | Mô tả phản hồi 1–5 và nhận xét như đã hoàn thiện hoặc chưa rõ trạng thái. Thực tế `extension/src/shared/config.ts` đặt `FEEDBACK_ENDPOINT_ENABLED = false` vì extension dùng `{request_id, rating, comment}` còn backend `/api/v1/feedback` (`metrics.py`) nhận `{request_id, helpful, reason}`. | Đã ghi rõ trạng thái "Đã làm một phần" cho FR-10, nêu rõ sai lệch schema và cờ khóa gửi mạng ở cả Charter và Final Report. |
| `FINAL_REPORT.md` mục 3.1 (FR-02) & `PROJECT_CHARTER.md` mục 1.4 | Mô tả chung nút kiểm chứng trên bài đăng Facebook/Reddit. Thực tế `reddit-adapter.ts` mới chèn nút ở trang chi tiết bài viết Reddit (`/comments/`), chưa hỗ trợ News Feed Reddit và Facebook (`facebook-adapter.ts` chỉ hỗ trợ bôi đen văn bản). | Đã sửa lại phạm vi chính xác ở Charter 1.4, 3.1 và Final Report FR-02, mục 9.2. |
| `FINAL_REPORT.md` mục 3.6 (`sources[]` & endpoints) | Bản nháp ghi `sources[]` có "tên miền", trong khi schema `Source` dùng trường `publisher` (và `analyze.py` ghi đè bằng `display_names` từ `trusted_domains.json` nếu khớp). Đồng thời `GET /api/v1/models`, `POST /api/v1/feedback`, `GET /api/v1/stats/summary` còn chỗ trống. | Đã đối chiếu đúng schema từ `response.py`, `analyze.py`, `metrics.py` và `deps.py`. |
| `FINAL_REPORT.md` mục 7.1 (`Các phương án so sánh`) | Bản nháp ghi phương án `(b)` là *"chỉ Google Fact Check"*. Thực tế `scripts/benchmark/run_benchmark.py` chạy chế độ `llm_factcheck` (dùng Gemini trích claim + Google Fact Check, tắt Tavily). | Đã sửa tên và mô tả 3 chế độ thành `(a) llm_only`, `(b) llm_factcheck`, `(c) full` khớp `run_benchmark.py` và `report.md`. |
| `FINAL_REPORT.md` mục 7.7 (`Khả năng mở rộng`) | Bản nháp ghi backend *"stateless"* cho từng yêu cầu. Thực tế rate limit và model cooldown lưu trong RAM từng process, còn cache/metrics lưu trong SQLite cục bộ. | Đã hiệu chỉnh để khớp đúng với hạn chế ở mục 3.9 và 9.2. |
| `FINAL_REPORT.md` mục 9.3 (`Hướng phát triển`) | Bản nháp liệt kê *"3. Cache theo nội dung"*, *"4. Xếp hạng độ uy tín nguồn theo danh sách tên miền"*, *"5. Nhiều truy vấn tìm kiếm cho mỗi claim"* như việc chưa làm. Thực tế cả 3 đã triển khai trong `analysis_cache.py`, `source_ranking.py` và `SEARCH_QUERY_LIMIT=2` (`analysis_orchestrator.py`). | Đã chuyển mục 9.3 sang hướng nâng cấp tiếp theo: semantic cache / Redis dùng chung, mở rộng `trusted_domains.json` cho báo Việt Nam, và tối ưu chi phí/độ trễ. |

---

## 3. Tính năng "Chưa làm" / làm một phần cần theo dõi trong mục Hạn chế & Hướng phát triển

Các mục dưới đây đã được ghi trung thực trong `FINAL_REPORT.md` mục **3.1**, **9.2 (Hạn chế)** và **9.3 (Hướng phát triển)**:

| Hạng mục | Hiện trạng trong mã nguồn | Vị trí đã ghi trong `FINAL_REPORT.md` |
|---|---|---|
| Nút kiểm chứng trên News Feed Facebook & Reddit | Chưa làm (mới có ở trang chi tiết Reddit `/comments/`) | Mục 3.1 (FR-02), 9.2, 9.3 |
| Adapter trình duyệt cho X (Twitter) | Chưa làm trên extension (backend `request.py` đã chấp nhận `platform="x"`) | Mục 1.3, 9.2, 9.3 |
| Gửi phản hồi 5 sao + nhận xét end-to-end | Đã dựng UI/message extension và API backend nhưng lệch schema, đang khóa qua `FEEDBACK_ENDPOINT_ENABLED = false` | Mục 3.1 (FR-10), 3.8, 9.2, 9.3 |
| Danh sách tên miền uy tín Việt Nam ở Backend | `source_ranking.py` đã có nhưng `trusted_domains.json` mới có 4 domain quốc tế | Mục 9.2, 9.3 |
| Lịch sử phân tích & Tóm tắt bài báo | Chưa làm | Mục 9.2, 9.3 |
| Chấm tay độ hợp lệ nguồn trích dẫn (Citation Validity) | Chưa có dữ liệu chấm tay cho đợt benchmark 17/11/2026 | Mục 7.3, 9.2, 9.3 |
| Khảo sát / thử nghiệm người dùng & Kiểm thử tải | Chưa có số liệu trong repo | Mục 7.6, 7.7, 9.2 |
| Xác thực động (OAuth/JWT) & Kho dùng chung (Redis/Postgres) | Chưa làm (đang dùng `VITE_EXTENSION_API_KEY` tĩnh và RAM/SQLite cục bộ) | Mục 7.7, 8, 9.2, 9.3 |

---

## 4. Ghi chú kiểm tra kỹ thuật & Câu hỏi chặn (nếu có)

- **Kiểm tra Mermaid (Mục F):** Không tìm thấy CLI `mmdc` trong môi trường hiện tại nên tất cả 4 sơ đồ Mermaid (`FINAL_REPORT.md` mục 3.3, 3.4, 3.5, 3.9) đã được rà soát cú pháp thủ công (đặt dấu ngoặc kép quanh nhãn có ký tự đặc biệt, kiểm tra khối `subgraph`/`alt`/`par`); nhóm cần kiểm tra hiển thị trực quan khi xuất PDF/Markdown preview trước khi nộp.
- **Kiểm tra lệnh test/lint (ngày 18/11/2026):**
  - Extension: `npm run lint`, `npm run typecheck` và `npm test` (`12/12` test) đều chạy thành công và pass.
  - Backend: `ruff check .` hiện báo **11 lỗi lint** tồn đọng trong `app/core/rate_limit.py`, `app/schemas/internal.py`, `app/services/__init__.py`, `app/services/base_service.py`, `tests/test_benchmark.py`, `tests/test_tavily_service.py`; `pytest` thu thập 149 test nhưng các test `asyncio` bị treo trong môi trường sandbox Windows khi tạo loopback socketpair — nhóm nên chạy lại `pytest -m "not e2e"` và `ruff check .` trực tiếp trên máy trước khi nộp để xác nhận CI xanh.
- **Không có điểm chặn bắt buộc hỏi thêm ngoài các mục `[CẦN ĐIỀN]` của người thật nêu tại mục 1.**
  - *Giả định tạm thời đang dùng:* link repository giữ theo `git remote -v` (`https://github.com/hoandng/trust-me-bro-2.0`) và mốc thời gian Charter mục 6 tổng hợp từ `git log`; nếu nhóm nộp từ repo khác hoặc có lịch trình chính thức khác, hãy chỉnh lại hai chỗ có nhãn `(cần người kiểm tra)`.
