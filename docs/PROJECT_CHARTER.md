# Project Charter

## TrustMeBro: Tiện ích mở rộng trình duyệt kiểm chứng thông tin bằng AI cho người dùng mạng xã hội

| | |
|---|---|
| **Thành viên** | **[CẦN ĐIỀN: Họ tên – MSSV – email]** |
| | **[CẦN ĐIỀN: Họ tên – MSSV – email]** |
| | **[CẦN ĐIỀN: Họ tên – MSSV – email]** |
| **Môn học / Giảng viên** | **[CẦN ĐIỀN: Tên môn học / Họ tên giảng viên]** |
| **Phiên bản / Ngày** | v1.0 – **[CẦN ĐIỀN: dd/mm/2026]** |
| **Mã nguồn** | `https://github.com/hoandng/trust-me-bro-2.0` (cần người kiểm tra) |

> **Ghi chú cho nhóm (xoá khối này trước khi nộp)**
> - Mọi chỗ ghi **[CẦN ĐIỀN]** là dữ liệu chỉ nhóm mới có (tên, ngày, số liệu đo thật). Không điền số liệu ước chừng như thể đã đo.
> - Phần "Mục tiêu đo được" và "Chỉ số thành công" ở mục 1.5 là **đề xuất**. Hãy hiệu chỉnh sau khi có kết quả benchmark, và ghi rõ ở báo cáo cuối nếu mục tiêu thay đổi.
> - Cấu trúc bám theo Project Charter mẫu của môn học (tổng quan, phạm vi, vai trò, nguồn lực, thời gian, rủi ro), bổ sung phần business theo yêu cầu của giảng viên.

---

## 1. Tổng quan dự án

### 1.1 Thực trạng

| Nội dung | Mô tả |
|---|---|
| **Vấn đề** | Người dùng mạng xã hội (đặc biệt là Facebook và Reddit) tiếp xúc với lượng lớn tin tức, tin đồn và thông tin sức khoẻ, tài chính, lừa đảo, thiên tai. Việc tự kiểm chứng đòi hỏi người dùng rời khỏi trang, tìm nhiều nguồn và đánh giá độ tin cậy, nên phần lớn người dùng bỏ qua bước này. |
| **Hạn chế của cách làm hiện nay** | Hỏi trực tiếp một chatbot AI có thể cho câu trả lời thiếu nguồn kiểm chứng hoặc sai (hallucination). Các trang kiểm chứng chuyên nghiệp chính xác nhưng chậm và chỉ phủ một phần tin đang lan truyền. Cả hai đều yêu cầu người dùng chủ động rời trang. |
| **Cơ hội** | Đưa việc kiểm chứng **vào ngay tại nơi người dùng đọc tin**, với kết luận ngắn gọn, có nguồn dẫn, trả về trong vài chục giây. |
| **Số liệu thị trường** | **[CẦN ĐIỀN: 2–3 số liệu về mức độ lan truyền tin giả / thói quen đọc tin trên mạng xã hội tại Việt Nam, kèm nguồn và năm]** |

### 1.2 Đối tượng người dùng

- **Nhóm mục tiêu ban đầu:** người dùng phổ thông, thường xuyên cập nhật tin tức qua mạng xã hội trên máy tính.
- **Persona chính:** **[CẦN ĐIỀN: ví dụ "Người 20–35 tuổi, hay phải đính chính tin sai với người thân trong nhóm gia đình"; bổ sung độ tuổi, thói quen, nỗi đau, điều họ mong muốn]**.
- **Bằng chứng nhu cầu:** **[CẦN ĐIỀN: kết quả khảo sát/phỏng vấn nếu đã thực hiện; nếu chưa có, ghi rõ là giả định cần kiểm chứng]**.

### 1.3 Mục đích của dự án

Xây dựng một hệ thống **kiểm chứng thông tin tích hợp AI** dưới dạng tiện ích mở rộng Chrome. Hệ thống tích hợp nội dung bài đăng trên mạng xã hội, mô hình ngôn ngữ lớn (LLM), công cụ tìm kiếm web và cơ sở dữ liệu kiểm chứng chuyên nghiệp để đưa ra kết luận **minh bạch, có nguồn, thừa nhận giới hạn** ("chưa đủ bằng chứng") thay vì đoán.

### 1.4 Mục tiêu của dự án

1. **Tích hợp nền tảng:** extension đọc nội dung trên Facebook và Reddit (qua cơ chế adapter), cho phép người dùng bôi đen đoạn văn bản (20–2000 ký tự) trên cả hai nền tảng hoặc bấm nút kiểm chứng trực tiếp trên trang chi tiết bài viết Reddit (`/comments/`).
2. **Tích hợp AI và dữ liệu:** backend kết hợp Google Gemini (`Interactions API`: trích claim, đánh giá bằng chứng), Tavily Search (nguồn tin web) và Google Fact Check Tools API (các claim đã được kiểm chứng).
3. **Kết quả minh bạch:** trả về kết luận (`Có vẻ đúng` / `Có vẻ sai sự thật` / `Đúng một phần` / `Chưa đủ bằng chứng`), giải thích ngắn tiếng Việt (có đánh dấu inline `✓`/`✗`/`?`), mức chắc chắn 3 vạch (`Thấp`/`Vừa`/`Cao`) và danh sách nguồn có ngày xuất bản (khi nhà cung cấp trả về).
4. **An toàn và kiểm soát chi phí:** xác thực bằng `X-API-Key` / `X-Admin-API-Key`, giới hạn tần suất theo IP/key/ngày, ngân sách thời gian tổng 25 giây, chống prompt injection, cache kết quả hợp lệ và không lưu nội dung bài đăng gốc.
5. **Đánh giá định lượng:** đo độ chính xác, độ trễ và chi phí mỗi lượt trên bộ dữ liệu 100 mẫu tiếng Việt có nhãn (`scripts/benchmark/dataset_vn_benchmark_100.csv`), so với phương án `llm_only` và `llm_factcheck`.

### 1.5 Chỉ số thành công (đề xuất theo cấu hình benchmark trong `scripts/benchmark/run_benchmark.py`, đối chiếu tại Final Report)

| Chỉ số | Mục tiêu đề xuất | Cách đo |
|---|---|---|
| Độ chính xác kết luận (accuracy, macro-F1) | Macro-F1 vượt phương án chỉ hỏi LLM (`llm_only`) `≥ +0.10` với kiểm định McNemar `p < 0.05` (ngưỡng `WORTH_MIN_F1_GAIN`, `WORTH_MAX_P_VALUE` trong `run_benchmark.py`) | Bộ dữ liệu 100 mẫu có nhãn (`scripts/benchmark/dataset_vn_benchmark_100.csv`) |
| Tỷ lệ kết luận sai nghiêm trọng (`true↔false`) | Không vượt quá phương án `llm_only` (`≤ critical_error_rate` của `llm_only`) | Ma trận nhầm lẫn trên bộ dữ liệu 100 mẫu |
| Độ hợp lệ của nguồn trích dẫn | **[CẦN ĐIỀN: % mục tiêu nguồn thật sự liên quan tới kết luận]** | Chấm tay nguồn trích dẫn trên mẫu thử |
| Độ trễ trung bình / p95 | `p95 ≤ 15.0` giây (ngưỡng `WORTH_MAX_P95_SECONDS` trong `run_benchmark.py`; timeout cứng toàn pipeline mặc định `25.0` giây) | Log hệ thống và kết quả benchmark |
| Chi phí mỗi lượt kiểm chứng | `≤ $0.0100` USD/lượt (ngưỡng `WORTH_MAX_COST_USD` trong `run_benchmark.py`) | Log token Gemini + credit Tavily × đơn giá |
| Mức hài lòng của người dùng thử | **[CẦN ĐIỀN: ngưỡng hài lòng mục tiêu (ví dụ ≥ 4/5) và quy mô n người thử nghiệm]** | Khảo sát người dùng thử, **[CẦN ĐIỀN: n người]** |

### 1.6 Kết quả mong muốn

- Extension Chrome hoạt động trên Facebook và Reddit, kèm backend FastAPI triển khai được (có sẵn cấu hình `docker-compose.yml`).
- Bộ tài liệu: Project Charter, SDS, Final Report.
- Báo cáo đánh giá có số liệu thật, phân tích lỗi và hạn chế.
- Bản demo chạy thật cho buổi bảo vệ.

---

## 2. Phân tích business sơ bộ

### 2.1 Đề xuất giá trị

> Người đọc tin trên mạng xã hội biết ngay "tin này có đáng tin không và vì sao" **ngay tại trang đang đọc**, trong vài chục giây, kèm nguồn để tự đối chiếu và sao chép tóm tắt để chia sẻ lại khi cần đính chính.

### 2.2 So sánh với giải pháp thay thế

| Tiêu chí | **TrustMeBro** | Hỏi trực tiếp chatbot AI | Google Fact Check Explorer | Trang kiểm chứng chuyên nghiệp |
|---|---|---|---|---|
| Dùng ngay trên trang đang đọc | **Có** (extension trên Facebook/Reddit, hiển thị trong Side Panel; kiểm chứng từ code) | Không (phải sao chép sang) (cần người kiểm tra) | Không (cần người kiểm tra) | Không (cần người kiểm tra) |
| Có nguồn dẫn kèm ngày | **Có** (Tavily trả `published_date` khi có; Fact Check hiện chưa trả ngày; kiểm chứng từ code) | **[CẦN ĐIỀN: xác minh đối thủ & dẫn nguồn]** | Có (cho claim đã kiểm chứng) (cần người kiểm tra) | Có (cần người kiểm tra) |
| Phủ tin mới chưa được kiểm chứng | **Có (qua Tavily Search)** — trên 35 mẫu `is_recent=yes` đạt Accuracy `65.7%` (F1 `0.461`) ngày 17/11, `65.7%` (F1 `0.559`) ngày 19/11 và `54.3%` (F1 `0.456`) ở đợt `full`-only 20/11 (`report.md`) | **[CẦN ĐIỀN: xác minh đối thủ & dẫn nguồn]** | Hạn chế (tương tự `llm_factcheck` đạt 3.0% độ phủ trên 100 mẫu VN) (cần người kiểm tra) | Hạn chế (cần người kiểm tra) |
| Thừa nhận khi chưa đủ bằng chứng | **Có** (dừng sớm khi `is_checkable=false`, trả `unverified` khi thiếu nguồn/timeout, trần confidence `≤ 0.4`) | **[CẦN ĐIỀN: xác minh đối thủ & dẫn nguồn]** | Không áp dụng (cần người kiểm tra) | Có (cần người kiểm tra) |
| Tốc độ | **`p50 = 8.39s / p95 = 15.56s`** (17/11), **`14.66s / 22.87s`** (19/11), **`7.01s / 20.00s`** (20/11) (`full`, 100 mẫu) | **[CẦN ĐIỀN: đối chiếu tốc độ thực tế của chatbot đối thủ; ghi chú: baseline `llm_only` trong benchmark đạt p50 1.89s / p95 5.34s (17/11) và 4.66s / 9.33s (19/11)]** | **[CẦN ĐIỀN: tốc độ thực tế trên web Explorer]** | **[CẦN ĐIỀN: tốc độ thực tế]** |
| Độ chính xác (benchmark) | **Acc `63.0%` / F1 `0.598`** (17/11), **Acc `72.0%` / F1 `0.694`** (19/11), **Acc `61.0%` / F1 `0.596`** (20/11) (`full`, `dataset_vn_benchmark_100.csv`) | **[CẦN ĐIỀN: đối chiếu đối thủ; ghi chú: baseline API `llm_only` đạt Acc 51.0%, Macro-F1 0.505]** | **[CẦN ĐIỀN: đối chiếu Explorer thực tế; ghi chú: chế độ `llm_factcheck` đạt Acc 16.0%, Macro-F1 0.085 (17/11)]** | Không áp dụng |

> Các ô có nhãn **(cần người kiểm tra)** hoặc **[CẦN ĐIỀN]** đối với đối thủ bên ngoài cần được nhóm đối chiếu trực tiếp hoặc bổ sung nguồn trích dẫn trước khi đưa vào báo cáo bảo vệ.

### 2.3 Mô hình kinh doanh dự kiến

| Hướng | Người trả tiền | Ghi chú |
|---|---|---|
| Freemium | Người dùng cá nhân (gói không giới hạn, lịch sử, cảnh báo) | **[CẦN ĐIỀN: mức sẵn lòng trả và lựa chọn mô hình kinh doanh chính của nhóm]** |
| Tài trợ / đối tác (B2B2C) | Ngân hàng, ví điện tử, nhà mạng muốn giảm lừa đảo cho khách | **[CẦN ĐIỀN: đánh giá khả thi nếu nhóm chọn/khảo sát]** |
| Tổ chức | Tòa soạn, trường học, dự án năng lực số | **[CẦN ĐIỀN: đánh giá khả thi nếu nhóm chọn/khảo sát]** |

**Đơn vị kinh tế (unit economics):**

```
Chi phí mỗi lượt = (số call Gemini × đơn giá) + (số call Tavily × đơn giá) + chi phí hạ tầng phân bổ
Chi phí thực tế mỗi lượt = Chi phí mỗi lượt × (1 − tỷ lệ cache hit)
```

- **Số liệu từ benchmark 100 mẫu chế độ `full` (`scripts/benchmark/results/`, chưa bật cache API, dùng đơn giá tham chiếu mặc định trong `run_benchmark.py`):** đợt `17-11-2026_18-34-33` là **$0.01713/lượt**; đợt `19-11-2026_17-02-53` là **$0.01714/lượt**; đợt `20-11-2026_14-49-30` giảm còn **$0.00942/lượt** (đạt ngưỡng `≤ $0.0100`).
- **Số liệu phát triển/thử nghiệm từ `backend/data/metrics.db` (`52` lượt trên `reddit`, không phải user test):** tỷ lệ cache hit **38.5% (`20/52`, độ trễ TB `3.1 ms`, chi phí `$0.0`)**; trên `32` lượt miss cache có độ trễ TB `10,934 ms`, trung bình `1.625` call Tavily và `3.25` call Fact Check (chưa có đơn giá cấu hình trong môi trường chạy thử nên chi phí USD các lượt miss chưa được ghi vào DB).
- **Số liệu vận hành/chi phí hạ tầng khi thử nghiệm người dùng thật:** **[CẦN ĐIỀN: chi phí hạ tầng phân bổ và số liệu thực tế khi pilot với người dùng]**.

---

## 3. Phạm vi dự án

### 3.1 Phạm vi bao gồm

1. Extension Chrome (Manifest V3) với adapter cho **Facebook** (bôi đen văn bản) và **Reddit** (bôi đen văn bản + nút kiểm chứng trực tiếp trên trang chi tiết `/comments/`), side panel hiển thị kết quả.
2. Backend (Python, FastAPI) với pipeline: trích claim → thu thập bằng chứng song song → đánh giá → hậu xử lý → trả kết quả.
3. Tích hợp **Google Gemini** (`Interactions API`), **Tavily Search** và **Google Fact Check Tools API**.
4. Cơ chế xác thực (`X-API-Key`, `X-Admin-API-Key`), giới hạn tần suất (IP/phút, key/ngày, global/ngày), ngân sách thời gian, cache kết quả (`analysis_cache`) và chống lạm dụng.
5. Thu thập chỉ số vận hành và phản hồi người dùng: **đã triển khai end-to-end** (`backend/app/core/metrics.py`, `backend/app/api/v1/metrics.py` với `POST /api/v1/feedback` hỗ trợ đánh giá 1–5 sao kèm `comment` tối đa 500 ký tự và tương thích ngược `helpful`/`reason`, `GET /api/v1/stats/summary`; phía extension đã bật `FEEDBACK_ENDPOINT_ENABLED = true` trong `extension/src/shared/config.ts`).
6. Bộ kiểm thử tự động (backend `pytest`, extension `node --test`), GitHub Actions CI, pre-commit, tài liệu (Project Charter, SDS, Final Report).
7. Đánh giá định lượng trên bộ dữ liệu 100 mẫu có nhãn (`dataset_vn_benchmark_100.csv`); thử nghiệm với người dùng (**[CẦN ĐIỀN: đã thực hiện / chưa thực hiện]**).

### 3.2 Phạm vi không bao gồm

1. Ứng dụng di động và web app độc lập (đưa vào hướng phát triển).
2. Kiểm chứng **ảnh và video** (chỉ xử lý văn bản).
3. Tự động gắn cảnh báo lên bài đăng khi người dùng chưa chủ động yêu cầu.
4. Huấn luyện hoặc tinh chỉnh mô hình AI (dùng mô hình có sẵn qua API).
5. Hệ thống tài khoản người dùng (OAuth/JWT), thanh toán.
6. Thay thế chuyên gia kiểm chứng hoặc đưa ra kết luận pháp lý.
7. Hỗ trợ adapter trình duyệt ngoài Facebook và Reddit (schema backend `AnalyzeRequest.platform` đã mở sẵn `"x"`, nhưng extension chưa có `XAdapter` và chưa cấp host permission cho X).

### 3.3 Giả định và ràng buộc

- Chất lượng kết quả phụ thuộc vào các API bên thứ ba (Gemini, Tavily, Google Fact Check) và hạn mức miễn phí/chi phí của chúng.
- Giao diện Reddit/Facebook thay đổi thường xuyên nên các selector bóc bài đăng trong `RedditAdapter` (`<shreddit-post>`, `[slot="title"]`, `[slot="text-body"]`, `content-href`) có thể cần cập nhật.
- Kết quả chỉ mang tính **tham khảo**, người dùng cần đối chiếu nguồn.

---

## 4. Vai trò và trách nhiệm

| Thành viên | Vai trò | Trách nhiệm chính |
|---|---|---|
| **[CẦN ĐIỀN]** | Backend và pipeline AI | Orchestrator, prompt, tích hợp Gemini/Tavily/Fact Check, độ chính xác |
| **[CẦN ĐIỀN]** | Extension và trải nghiệm người dùng | Adapter Facebook/Reddit, side panel, UI/UX, kiểm thử giao diện |
| **[CẦN ĐIỀN]** | Đánh giá, bảo mật, tài liệu | Bộ dữ liệu và benchmark, khảo sát người dùng, bảo mật, báo cáo |

> Các thành viên vẫn hỗ trợ và nắm được phần công việc của nhau. **[CẦN ĐIỀN: điều chỉnh theo thực tế phân công của nhóm]**

---

## 5. Nguồn lực

| Nhóm | Công nghệ / tài nguyên |
|---|---|
| **Backend** | Python 3.11+ (CI dùng 3.13, Docker dùng `python:3.12-slim`), FastAPI (`0.141.1`), httpx (`0.28.1`), Pydantic v2 (`2.13.5`), pydantic-settings (`2.12.0`), Uvicorn (`0.54.0`), SQLite (`backend/data/metrics.db`) |
| **AI và dữ liệu** | Google Gemini API (`google-genai` `2.27.0` Interactions API; model mặc định `gemini-3.1-flash-lite`, ví dụ pool dự phòng trong `.env.example` gồm `gemini-3.1-flash-lite`, `gemini-3.5-flash`, `gemini-2.5-flash-lite`), Tavily Search API, Google Fact Check Tools API |
| **Extension** | TypeScript (`~6.0.3`), Node.js (`20.19+` / `22.13+` / `24+`, CI dùng Node 20), Chrome Extension Manifest V3, Vite (`^8.3.1`), Chrome Side Panel API |
| **Chất lượng** | `pytest` (`9.1.1`), `pytest-asyncio` (`1.4.0`), `respx` (`0.23.1`), `ruff` (`0.16.9`), ESLint (`^10.11.0`), `tsc --noEmit`, `node --test` (`extension/tests/run-tests.mjs`), GitHub Actions CI (`.github/workflows/ci.yml`), `pre-commit` + `gitleaks` |
| **Hạ tầng** | **[CẦN ĐIỀN: nơi triển khai backend thực tế của nhóm (cục bộ / Render / Railway / ...)]** (repo có sẵn `backend/Dockerfile` và `docker-compose.yml` cho chạy container cục bộ) |
| **Chi phí / quota** | **[CẦN ĐIỀN: gói API đang dùng, hạn mức quota và ngân sách của nhóm]** (chi phí benchmark 100 mẫu 3 chế độ theo đơn giá tham chiếu trong `summary.json` là `$1.7519`) |

---

## 6. Thời gian dự kiến

| Giai đoạn | Nội dung chính | Thời gian (cần người kiểm tra) | Sản phẩm bàn giao |
|---|---|---|---|
| 1. Nghiên cứu và thiết kế | Khảo sát vấn đề, chọn kiến trúc, scaffold extension/backend | 28/09/2026 – 01/10/2026 (theo `git log`, cần người kiểm tra) | Charter, kiến trúc sơ bộ |
| 2. Backend pipeline | Trích claim, tích hợp Tavily/Fact Check, đánh giá bằng chứng, chọn & fallback model | 01/10/2026 – 04/11/2026 (theo `git log`, cần người kiểm tra) | API `/analyze`, `/models` hoạt động |
| 3. Extension | Adapter Facebook/Reddit, selection controller, side panel, nút kiểm chứng Reddit | 28/09/2026 – 01/11/2026 (theo `git log`, cần người kiểm tra) | Extension chạy end-to-end |
| 4. Bảo mật, vận hành, UX | Rate limit, nâng cấp A1–A3, SQLite metrics/feedback (B1), cache (C1), UX side panel (C2) | 02/10/2026 & 10/11/2026 – 15/11/2026 (theo `git log`, cần người kiểm tra) | Bản demo ổn định |
| 5. Đánh giá và tài liệu | Bộ dữ liệu VN 100 mẫu, benchmark B2, hoàn thiện tài liệu (Charter, Final Report) | 11/11/2026 – 20/11/2026 (theo `git log`, cần người kiểm tra) | Bộ tài liệu, số liệu benchmark |
| Nộp sản phẩm | Nộp Project Charter, SDS, Final Report lên thư mục chung | **20/11/2026** | Bộ hồ sơ nộp |
| Bảo vệ | Theo lịch của lớp | **[CẦN ĐIỀN: ngày bảo vệ của nhóm]** | Báo cáo in nộp cho Khoa |

---

## 7. Rủi ro và biện pháp quản lý

| # | Rủi ro | Mức độ | Biện pháp |
|---|---|---|---|
| 1 | AI kết luận sai (hallucination), gây hiểu lầm cho người dùng | Cao | Chỉ kết luận dựa trên bằng chứng đã tìm được; lọc URL không có trong nguồn (`gemini_service.py`); trả `unverified` và trần confidence `≤ 0.4` khi thiếu căn cứ; hiển thị cảnh báo `"AI có thể sai. Hãy tự đối chiếu với các nguồn uy tín."` |
| 2 | Nguồn tìm được kém uy tín hoặc chỉ liên quan gián tiếp | Cao | Xếp hạng nguồn theo `tier1`/`tier2`/`default` (`trusted_domains.json` gồm 32 domain với 28 domain Việt Nam + `source_ranking.py`); hiển thị nhãn quan điểm (`Ủng hộ`/`Phản bác`/`Liên quan`) và ghi chú khi tất cả nguồn đều trung lập |
| 3 | Tin cũ được đăng lại như tin mới | Trung bình | Đưa ngày hiện tại theo múi giờ `Asia/Ho_Chi_Minh` vào prompt đánh giá; lưu và hiển thị `published_date` của nguồn (khi Tavily cung cấp) |
| 4 | Prompt injection từ nội dung bài đăng hoặc nguồn web | Cao | Tách dữ liệu trong thẻ `<post>...</post>`, trung hòa `[[` và `]]` bằng `neutralize_marker_delimiters()`, làm sạch ký hiệu đánh dấu ở đầu ra và kiểm tra JSON bằng Pydantic |
| 5 | Nền tảng đổi giao diện làm adapter hỏng | Trung bình | Cô lập selector trong adapter (`RedditAdapter` dùng `<shreddit-post>`, `[slot="title"]`, `[slot="text-body"]`); giữ chế độ bôi đen văn bản (`window.getSelection()`) trên cả Facebook và Reddit làm phương án dự phòng |
| 6 | Hết hạn mức hoặc vượt ngân sách API | Trung bình | Xoay vòng model qua `GeminiModelPool` khi gặp `429`; giới hạn IP (`10/phút`), key (`100/ngày`), kill switch tổng (`1000/ngày`); cache kết quả hợp lệ trong `analysis_cache` |
| 7 | Độ trễ cao khiến người dùng bỏ dở | Trung bình | Gọi song song Fact Check và Tavily; áp ngân sách thời gian tổng mặc định `25.0s` (`ANALYSIS_TIMEOUT_SECONDS`); trả kết quả giảm cấp kèm `service_status` khi có dịch vụ lỗi/timeout |
| 8 | Lộ khoá API hoặc dữ liệu cá nhân | Cao | Không lưu nội dung bài đăng gốc vào DB/log; dùng `JSONFormatter` che khóa và tắt `INFO` của `httpx`; pre-commit `gitleaks`; ghi rõ rủi ro của `VITE_EXTENSION_API_KEY` nhúng trong extension |
| 9 | Người dùng không chủ động kiểm chứng (thiếu adoption) | Trung bình | Đặt nút kiểm chứng trực tiếp trên trang chi tiết bài đăng Reddit (`/comments/`); khảo sát hành vi để tiếp tục mở rộng lên News Feed |
| 10 | Phụ thuộc dịch vụ bên thứ ba thay đổi chính sách hoặc giá | Trung bình | Tách lớp tích hợp (`BaseService` facade) để thay thế nguồn dễ dàng; theo dõi chi phí ước tính qua `metrics.py` và `/api/v1/stats/summary` |
| 11 | Trách nhiệm khi kết luận sai | Trung bình | Nêu rõ kết quả chỉ mang tính tham khảo trong giao diện và bản sao chép chia sẻ, cung cấp đường dẫn nguồn để người dùng tự đối chiếu |

---

## 8. Tiêu chí chấp nhận và các bên liên quan

**Tiêu chí chấp nhận:**
1. Người dùng cài extension, bôi đen đoạn văn bản trên Facebook/Reddit (hoặc bấm nút kiểm chứng trên trang chi tiết Reddit) và nhận kết quả có nguồn trong giới hạn thời gian cấu hình.
2. Hệ thống không trả kết luận "đúng" hoặc "sai" khi không có bằng chứng (giữ kết luận `unverified` với trần độ tin cậy `0.3–0.4`).
3. Bộ kiểm thử tự động và CI xanh (lưu ý hiện trạng tới commit `f491d97`: extension lint/typecheck/12 test/build pass; backend thu thập `151` test với `test_source_ranking.py` `13/13` pass nhưng test `asyncio` chưa chạy trọn vẹn trong sandbox Windows, còn `11` cảnh báo `ruff` và lỗi `AttributeError` `extraction.tool_calls` trong `analysis_orchestrator.py` cần xử lý).
4. Có báo cáo đánh giá với số liệu benchmark thật và phân tích lỗi, hạn chế.

**Các bên liên quan:** giảng viên (đánh giá), nhóm phát triển, người dùng thử, **[CẦN ĐIỀN: đối tác/tổ chức tham gia nếu có (hoặc ghi "Không có")]**.
