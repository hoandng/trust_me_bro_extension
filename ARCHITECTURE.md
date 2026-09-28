# ARCHITECTURE.md

> Dự án: **Trình mở rộng (browser extension) kiểm tra độ tin cậy bài đăng mạng xã hội**
> Phiên bản tài liệu: v0.1 — Demo trên Facebook

## 1. Kiến trúc tổng quan

Mô hình: **Client-Server**, trong đó Client là Chrome Extension (Manifest V3), Server là REST API backend độc lập đóng vai trò "orchestrator" gọi nhiều dịch vụ AI/fact-check bên ngoài rồi tổng hợp kết quả.

```
[Facebook page]
      │  (user bôi đen text → chọn "Phân tích đoạn văn này")
      ▼
[Content Script] ──postMessage──► [Background/Service Worker]
      │                                    │
      │                                    ▼
      │                          [Backend API] (FastAPI)
      │                                    │
      │                     ┌──────────────┼───────────────┐
      │                     ▼              ▼               ▼
      │              [Fact Check API]  [Gemini API]   [Tavily API]
      │                     └──────────────┬───────────────┘
      │                                    ▼
      │                         [Orchestrator tổng hợp
      │                          + chấm điểm + trích nguồn]
      ▼                                    │
[Side Panel UI] ◄───────response JSON──────┘
(hiển thị kết quả, độ tin cậy, nguồn trích dẫn)
```

**Vì sao chọn kiến trúc này:**
- Tách biệt extension (chỉ làm UI + bắt sự kiện) khỏi backend (chứa toàn bộ logic AI, API key) → **bảo mật**: API key của Gemini/Tavily/Fact Check không bao giờ nằm trong code extension (client-side), tránh bị lộ khi người dùng inspect extension.
- Backend đóng vai trò orchestrator, dễ thêm/bớt/nâng cấp nguồn dữ liệu (thêm API mới) mà không cần cập nhật extension.
- Dễ mở rộng sang nền tảng khác (X, Reddit...) vì phần logic phân tích nằm hoàn toàn ở backend, chỉ cần viết thêm content script tương ứng cho từng nền tảng.

## 2. Các thành phần chính

### 2.1. Browser Extension (Client)
- **Nền tảng:** Chrome Extension Manifest V3 (tương thích Edge, và có thể port sang Firefox sau)
- **Ngôn ngữ:** JavaScript/TypeScript (khuyến nghị TypeScript để dễ bảo trì khi mở rộng)
- **Các thành phần:**
  | Module | Vai trò |
  |---|---|
  | `content-script/` | Inject vào trang Facebook, bắt sự kiện bôi đen text, hiển thị nút nổi "Phân tích đoạn văn này" |
  | `background/` (service worker) | Nhận request từ content script, gọi backend API, quản lý state, xử lý message passing |
  | `sidepanel/` | UI hiển thị kết quả phân tích (dùng Chrome Side Panel API) |
  | `shared/` | Types, constants, utils dùng chung |

- **Cách bắt sự kiện bôi đen (MVP):**
  1. Content script lắng nghe sự kiện `selectionchange` / `mouseup` trên DOM Facebook
  2. Khi có văn bản được chọn → hiển thị nút nổi nhỏ "🔍 Phân tích đoạn văn này" cạnh vùng chọn
  3. User click → gửi text qua `chrome.runtime.sendMessage` đến background script
  4. Background gọi backend API → nhận kết quả → mở Side Panel hiển thị

> Ghi chú thiết kế để dễ nâng cấp: Content script nên viết theo **adapter pattern** — mỗi mạng xã hội (Facebook, X, Reddit) có 1 file adapter riêng implement chung 1 interface (`getSelectedText()`, `injectButton()`, `getPostContext()`...). Bản demo chỉ cần `facebook-adapter.ts`, sau này thêm `x-adapter.ts`, `reddit-adapter.ts` mà không đụng vào core logic.

### 2.2. Backend API (Server)
- **Framework:** Python + FastAPI
- **Kiến trúc API:** REST, 1 endpoint chính `POST /api/v1/analyze`
- **Cấu trúc thư mục đề xuất:**
  ```
  backend/
  ├── app/
  │   ├── main.py                 # entrypoint FastAPI
  │   ├── api/
  │   │   └── v1/
  │   │       └── analyze.py      # route /analyze
  │   ├── core/
  │   │   ├── config.py           # đọc env, settings
  │   │   ├── security.py         # rate limit, API key validation, CORS
  │   │   └── logging.py
  │   ├── services/                # MODULE HOÁ theo từng nguồn dữ liệu
  │   │   ├── factcheck_service.py # gọi Google Fact Check Tools API
  │   │   ├── gemini_service.py    # gọi Gemini API (phân tích/tóm tắt/đánh giá)
  │   │   ├── tavily_service.py    # gọi Tavily API (tìm kiếm nguồn tham khảo)
  │   │   └── base_service.py      # interface chung: mỗi service implement `async def check(text) -> SourceResult`
  │   ├── orchestrator/
  │   │   └── analysis_orchestrator.py  # gọi song song các service, tổng hợp, chấm điểm cuối
  │   ├── schemas/
  │   │   ├── request.py          # AnalyzeRequest (text, url, platform...)
  │   │   └── response.py         # AnalyzeResponse (verdict, score, sources[], explanation)
  │   └── utils/
  ├── tests/
  ├── .env.example
  ├── requirements.txt
  └── Dockerfile
  ```

- **Vì sao module hoá theo `services/` + `orchestrator/`:**
  - Mỗi API bên ngoài (Fact Check, Gemini, Tavily) là 1 service độc lập, cùng implement 1 interface (`base_service.py`) → khi Fact Check API đổi version hoặc bạn muốn thay bằng API khác, chỉ sửa 1 file, không ảnh hưởng phần còn lại.
  - `orchestrator` không biết chi tiết implementation của từng service, chỉ gọi qua interface chung → dễ thêm service mới (chỉ cần đăng ký thêm vào danh sách service mà orchestrator gọi).
  - Đây là pattern chuẩn cho sản phẩm thương mại: tách "nguồn dữ liệu" (data source) khỏi "logic nghiệp vụ" (business logic).

### 2.3. Luồng xử lý tại Orchestrator (logic lõi)
1. Nhận text từ request
2. Gọi song song (`asyncio.gather`):
   - `factcheck_service`: tìm claim đã được fact-check trước đó liên quan đến nội dung
   - `tavily_service`: tìm kiếm nguồn tin tức/bài viết liên quan để đối chiếu
   - `gemini_service`: phân tích ngữ nghĩa, tóm tắt claim chính, đối chiếu với kết quả từ 2 API trên, sinh ra đánh giá + giải thích
3. Tổng hợp kết quả → trả về:
   ```json
   {
     "verdict": "likely_false | likely_true | unverified | mixed",
     "confidence_score": 0.0,
     "explanation": "Giải thích ngắn gọn tại sao",
     "sources": [
       {"title": "...", "url": "...", "publisher": "...", "relevance": "..."}
     ]
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
- Chỉ hỗ trợ Facebook, DOM selector có thể hỏng khi Facebook đổi giao diện → cần thiết kế adapter dễ sửa (mục 2.1).
- Static API key giữa extension–backend chưa đủ an toàn cho production.

## 6. Định hướng mở rộng (đã tính trước trong kiến trúc)
- Thêm mạng xã hội mới → thêm adapter mới trong extension, không đổi backend.
- Thêm API/nguồn dữ liệu mới → thêm 1 service mới trong `services/`, đăng ký vào orchestrator.
- Chế độ tự động phân tích khi click vào post (thay vì bôi đen) → chỉ cần thêm 1 adapter method `injectButtonOnEachPost()`, luồng backend giữ nguyên.
- Khi cần lưu lịch sử/cache → thêm `database/` layer + Redis cache trước các service calls, không ảnh hưởng orchestrator logic.
