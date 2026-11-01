# ARCHITECTURE.md

> Dự án: **Trình mở rộng (browser extension) kiểm tra độ tin cậy bài đăng mạng xã hội**
> Phiên bản tài liệu: v0.2 — Extension module theo tính năng (Facebook, Reddit)

## 1. Kiến trúc tổng quan

Mô hình: **Client-Server**, trong đó Client là Chrome Extension (Manifest V3), Server là REST API backend độc lập đóng vai trò "orchestrator" gọi nhiều dịch vụ AI/fact-check bên ngoài rồi tổng hợp kết quả.

```text
[Facebook / Reddit]
        │ chọn văn bản hoặc bấm nút bài viết
        ▼
[Content script] ──chrome.runtime.sendMessage──► [Background service worker]
                                                        │ HTTP
                                                        ▼
                                                   [FastAPI]
                                                        │
                                                [Orchestrator]
                                                        │
                                         [Gemini / Fact Check / Tavily]
                                                        │ kết quả
                                                        ▼
[Side panel] ◄──theo dõi chrome.storage.session── [Background service worker]
```

**Vì sao chọn kiến trúc này:**
- Tách biệt extension (chỉ làm UI + bắt sự kiện) khỏi backend (chứa toàn bộ logic AI, API key) → **bảo mật**: API key của Gemini/Tavily/Fact Check không bao giờ nằm trong code extension (client-side), tránh bị lộ khi người dùng inspect extension.
- Backend đóng vai trò orchestrator, dễ thêm/bớt/nâng cấp nguồn dữ liệu (thêm API mới) mà không cần cập nhật extension.
- Dễ mở rộng sang nền tảng khác (X, Reddit...) vì phần logic phân tích nằm hoàn toàn ở backend, chỉ cần bổ sung adapter trong content script cho từng nền tảng.

## 2. Các thành phần chính

### 2.1. Browser Extension (Client)

- **Kiến trúc tổ chức file:** Feature-based modular architecture, tách điểm chạy của Manifest V3 khỏi module tính năng và hạ tầng.
- **Công nghệ:** TypeScript strict, HTML/CSS và DOM thuần, Vite. Manifest được tạo bằng plugin nội bộ trong `extension/vite.config.ts`.
- **Nền tảng hiện có:** Facebook và Reddit. Reddit có thêm nút kiểm chứng trong trang chi tiết bài viết.

```text
extension/
├── src/
│   ├── entrypoints/
│   │   ├── background.ts           # đăng ký message listener
│   │   ├── content.ts              # khởi tạo tương tác trên trang
│   │   └── sidepanel/              # HTML và khởi tạo side panel
│   ├── features/
│   │   └── analysis/
│   │       ├── types.ts            # request, response backend/UI, trạng thái
│   │       ├── state-store.ts      # khóa và trạng thái phân tích theo tab
│   │       ├── background/
│   │       │   ├── handle-analysis.ts # điều phối loading → API → success/error
│   │       │   ├── analysis-api.ts    # endpoint phân tích
│   │       │   └── map-response.ts    # chuyển response backend thành dữ liệu UI
│   │       ├── content/
│   │       │   ├── selection-controller.ts
│   │       │   ├── adapters/       # interface, registry, Facebook, Reddit
│   │       │   └── ui/             # nút nổi trong Shadow DOM
│   │       └── sidepanel/
│   │           ├── controller.ts  # sự kiện tab, subscription, retry
│   │           ├── render.ts      # DOM, loading, kết quả, sao chép
│   │           └── index.css
│   ├── infrastructure/
│   │   ├── api/backend-client.ts   # HTTP, header, timeout, lỗi mạng
│   │   └── storage/session-store.ts # adapter chrome.storage.session
│   └── shared/
│       ├── messages.ts            # hợp đồng và kiểm tra message đầu vào
│       └── config.ts              # đường dẫn side panel dùng chung với Vite
├── tests/                         # kiểm tra module với API/Chrome mock
├── public/icons/
└── vite.config.ts
```

**Quy tắc phụ thuộc:**

- `entrypoints/` chỉ đăng ký listener và khởi tạo tính năng.
- `features/<tên>/` giữ logic, dữ liệu và giao diện của tính năng đó. Module background không import DOM của content script/side panel; content script không import HTTP client hoặc logic background.
- Module dùng ở cả background và side panel đặt ở gốc tính năng, như `analysis/state-store.ts`.
- `infrastructure/` bao bọc HTTP và Chrome Storage; không import logic từ `features/` hoặc `entrypoints/`.
- `shared/` chứa hợp đồng giao tiếp và cấu hình dùng chung. `shared/messages.ts` chỉ import **type** của tính năng, không kéo mã thực thi của tính năng sang ngữ cảnh khác.
- Mọi import kiểu dữ liệu dùng `import type` để tránh đưa mã không cần thiết vào bundle.

**Luồng phân tích hiện tại:**

1. `entrypoints/content.ts` khởi tạo selection controller và chọn adapter theo URL.
2. Nút nổi hoặc nút Reddit gửi `ANALYZE_REQUEST` qua `chrome.runtime.sendMessage`.
3. `entrypoints/background.ts` kiểm tra hợp đồng message rồi chuyển cho `handle-analysis.ts`.
4. Handler mở side panel, ghi `loading`, gọi `analysis-api.ts`; HTTP client gửi `POST /api/v1/analyze` với timeout 60 giây.
5. `map-response.ts` đổi verdict và confidence của backend sang dữ liệu UI; handler ghi `success` hoặc `error`.
6. Side panel đọc và theo dõi `tabState_<tabId>` trong `chrome.storage.session`; controller chuyển trạng thái cho renderer.

`chrome.storage.session` hiện giữ trạng thái giao diện theo tab; **chưa có cache kết quả**. Không dùng biến toàn cục của service worker làm nơi lưu trạng thái cần giữ giữa các lần worker chạy.

**Mở rộng:**

- Thêm mạng xã hội: tạo adapter implement `PlatformAdapter` trong `features/analysis/content/adapters/`, đăng ký trong `index.ts` và cập nhật matches/host permissions ở Vite.
- Thêm tóm tắt bài báo: tạo `features/article-summary/` với `types.ts`, `content/`, `background/`, `sidepanel/`; thêm hợp đồng message và nối tại các entrypoint. Xử lý AI vẫn nằm ở backend.
- Thêm cache: tạo adapter `infrastructure/cache/` khi triển khai, để từng tính năng tự quyết định khóa, TTL và điều kiện bỏ qua cache. Tách cache kết quả khỏi trạng thái UI theo tab.
- Thêm service AI/search bên ngoài: triển khai ở backend; extension chỉ thêm API client hoặc mapper của tính năng khi hợp đồng backend thay đổi.

Chi tiết phát triển, debug và kiểm tra thủ công: [`extension/README.md`](extension/README.md).

### 2.2. Backend API (Server)
- **Framework:** Python + FastAPI
- **Kiến trúc API:** REST, 1 endpoint chính `POST /api/v1/analyze`
- **Cấu trúc thư mục thực tế:**
  ```
  backend/
  ├── app/
  │   ├── main.py                 # entrypoint FastAPI
  │   ├── api/
  │   │   ├── deps.py             # Dependency injection (orchestrator, rate limiter)
  │   │   └── v1/
  │   │       └── analyze.py      # route /analyze
  │   ├── core/
  │   │   ├── config.py           # đọc env, settings
  │   │   ├── rate_limit.py       # rate limiter (chống spam)
  │   │   └── logging.py          # cấu hình logger
  │   ├── prompts/
  │   │   └── gemini_prompts.py   # Các mẫu prompt chi tiết cho Gemini
  │   ├── services/               # MODULE HOÁ theo từng nguồn dữ liệu
  │   │   ├── factcheck_service.py# gọi Google Fact Check Tools API
  │   │   ├── gemini_service.py   # gọi Gemini API (phân tích/tóm tắt/đánh giá)
  │   │   ├── tavily_service.py   # gọi Tavily API (tìm kiếm nguồn tham khảo)
  │   │   └── base_service.py     # interface chung
  │   ├── orchestrator/
  │   │   └── analysis_orchestrator.py  # gọi logic các service, tổng hợp kết quả
  │   └── schemas/
  │       ├── internal.py         # context / schemas dùng nội bộ
  │       ├── request.py          # AnalyzeRequest (text, url, platform...)
  │       └── response.py         # AnalyzeResponse (verdict, score, sources[], explanation)
  ├── tests/                      # Unit/Integration tests
  ├── .env.example
  └── requirements.txt
  ```

- **Vì sao module hoá theo `services/` + `orchestrator/`:**
  - Mỗi API bên ngoài (Fact Check, Gemini, Tavily) là 1 service độc lập, cùng implement 1 interface (`base_service.py`) → khi Fact Check API đổi version hoặc bạn muốn thay bằng API khác, chỉ sửa 1 file, không ảnh hưởng phần còn lại.
  - `orchestrator` không biết chi tiết implementation của từng service, chỉ gọi qua interface chung → dễ thêm service mới (chỉ cần đăng ký thêm vào danh sách service mà orchestrator gọi).
  - Đây là pattern chuẩn cho sản phẩm thương mại: tách "nguồn dữ liệu" (data source) khỏi "logic nghiệp vụ" (business logic).

### 2.3. Luồng xử lý tại Orchestrator (logic lõi - Đã cập nhật v0.2)
1. **Giai đoạn 0 (Trích xuất & Lọc):**
   - `gemini_service.extract_claims` phân tích văn bản để tìm claim chính, ngôn ngữ và các câu query tối ưu.
   - Nếu `is_checkable=false` (không có yếu tố kiểm chứng được như ý kiến cá nhân, câu hỏi) -> trả ngay verdict "unverified" kèm giải thích, không gọi tiếp API để tiết kiệm chi phí.
2. **Giai đoạn 1 (Thu thập bằng chứng):**
   - Gọi song song (`asyncio.gather`):
     - `factcheck_service`: tìm claim đã được fact-check trước đó.
     - `tavily_service`: tìm kiếm nguồn tin tức/bài viết liên quan đối chiếu.
3. **Giai đoạn 2 (Đánh giá tổng hợp):**
   - `gemini_service.assess`: nhận toàn bộ sources thu thập được từ Giai đoạn 1 và thực hiện đánh giá cuối cùng.
   - Orchestrator áp dụng các quy tắc:
     - Ưu tiên nguồn từ Fact Check: nếu có kết quả rõ ràng, chỉnh lại confidence và đưa lên đầu danh sách sources.
     - Lọc trùng URL, giới hạn tối đa 8 nguồn.
     - Xử lý lỗi linh hoạt (degraded result) nếu 1 service sập, hoặc timeout.
     - Đảm bảo nhất quán giữa `verdict` và `confidence_score`.
4. Tổng hợp kết quả → trả về:
   ```json
   {
     "verdict": "likely_false | likely_true | unverified | mixed",
     "confidence_score": 0.0,
     "explanation": "Giải thích ngắn gọn tại sao",
     "sources": [
       {"title": "...", "url": "...", "publisher": "...", "relevance": "..."}
     ],
     "service_status": {
        "factcheck": "ok|error|empty",
        "tavily": "ok|error|empty",
        "gemini": "ok|error|empty"
     }
   }
   ```

## 3. Bảo mật (quan trọng — đọc kỹ trước khi code)

| Vấn đề | Giải pháp |
|---|---|
| API key (Gemini, Tavily, Fact Check) | **Chỉ lưu ở backend** (biến môi trường `.env`, không commit). Extension không bao giờ chứa API key. |
| Giao tiếp Extension ↔ Backend | Bắt buộc HTTPS. Xác thực bằng token/API key riêng của extension (không phải key của Gemini/Tavily) để tránh backend bị lạm dụng bởi bên thứ ba. |
| Rate limiting | Backend giới hạn số request/IP hoặc /extension-instance để tránh spam, tốn quota API trả phí. |
| Dữ liệu người dùng | Ở bản demo: **không lưu** nội dung bài đăng, xử lý real-time rồi trả kết quả, không ghi log nội dung text đầy đủ — chỉ log metadata (thời gian, độ dài text, kết quả). |
| CORS | Backend chỉ chấp nhận request có origin là extension ID cụ thể, không mở public cho mọi origin. |
| Input validation | Giới hạn độ dài text gửi lên (tránh lạm dụng), sanitize input trước khi gửi tới các API ngoài. |

> **Giả định của Claude:** Vì bản demo "chưa cần database", token xác thực giữa extension–backend có thể dùng 1 static API key nhúng vào extension lúc build (chấp nhận được cho demo nội bộ, **không dùng cách này khi phát hành công khai** — khi đó cần OAuth hoặc issued token per install). Xác nhận lại nếu bạn muốn làm chuẩn hơn ngay từ đầu.

## 4. Các API bên ngoài sử dụng (bản demo)

| API | Mục đích | Ghi chú |
|---|---|---|
| Google Fact Check Tools API | Tìm claim đã được các tổ chức fact-check xác minh trước đó | Miễn phí, có giới hạn quota |
| Gemini API | Phân tích ngữ nghĩa, tóm tắt, tổng hợp đánh giá cuối, sinh giải thích | Cần API key, tính phí theo token |
| Tavily API | Search engine tối ưu cho AI, tìm nguồn tin liên quan real-time | Cần API key, có free tier |

## 5. Giới hạn/nợ kỹ thuật đã biết (bản demo)
- Chưa có database → không lưu lịch sử, không cache → mỗi lần phân tích đều tốn API call thật (cân nhắc thêm cache ở bản sau để tiết kiệm chi phí).
- Hỗ trợ Facebook và Reddit; DOM selector có thể hỏng khi nền tảng đổi giao diện → cần thiết kế adapter dễ sửa (mục 2.1).
- Static API key giữa extension–backend chưa đủ an toàn cho production.
- Google Fact Check Tools API có độ phủ dữ liệu tiếng Việt còn hạn chế, có thể thường xuyên trả về trạng thái rỗng ("empty") khi truy vấn nội dung tiếng Việt.

## 6. Định hướng mở rộng (đã tính trước trong kiến trúc)
- Thêm mạng xã hội mới → thêm adapter mới trong extension, không đổi backend.
- Thêm API/nguồn dữ liệu mới → thêm 1 service mới trong `services/`, đăng ký vào orchestrator.
- Chế độ tự động phân tích khi click vào post (thay vì bôi đen) → chỉ cần thêm 1 adapter method `injectButtonOnEachPost()`, luồng backend giữ nguyên.
- Khi cần lưu lịch sử/cache → thêm `database/` layer + Redis cache trước các service calls, không ảnh hưởng orchestrator logic.
