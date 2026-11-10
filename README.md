# Trust Me Bro Extension

Dự án này là một **Browser Extension (Trình mở rộng trình duyệt)** hỗ trợ kiểm tra độ tin cậy của nội dung trên mạng xã hội. Extension cho phép người dùng chọn một đoạn văn bản trên Facebook hoặc Reddit và nhận được phân tích, đánh giá, kèm theo các nguồn tham khảo liên quan về tính xác thực của thông tin đó.

## 🌟 Tính năng (Features)

- **Phân tích theo vùng bôi đen & theo bài viết**:
  - Bôi đen một đoạn văn bản (20–2000 ký tự) trên **Facebook** hoặc **Reddit**, một nút nổi sẽ hiện ra ngay phía trên vùng chọn.
  - Trên trang chi tiết bài viết **Reddit** (`/comments/`), extension tự động bóc tách tiêu đề/nội dung và chèn nút **"Kiểm chứng bài viết"** trực tiếp vào bài đăng.
- **Orchestrator Backend (Pipeline 3 giai đoạn)**: Backend viết bằng FastAPI điều phối các nguồn xác thực:
  - **Gemini API (Interactions API)**: Tách khẳng định chính và câu truy vấn tìm kiếm (Stage 0), sau đó tổng hợp bằng chứng để đưa ra kết luận cuối cùng (`verdict`), điểm tin cậy (`confidence_score`) và giải thích tiếng Việt (Stage 2).
  - **Google Fact Check Tools API**: Đối chiếu tuyên bố (claims) đã được các tổ chức kiểm chứng quốc tế xác minh (chạy song song ở Stage 1).
  - **Tavily Search API**: Tìm kiếm thời gian thực để thu thập các bài báo, nguồn tin liên quan đối chứng (chạy song song ở Stage 1).
- **Side Panel UI trực quan**: Hiển thị trạng thái theo từng tab độc lập, tiến trình xử lý 3 bước, nhãn kết luận kèm độ tin cậy, giải thích chi tiết, danh sách nguồn kèm thái độ (`Ủng hộ` / `Bác bỏ` / `Trung lập`), cảnh báo khi một dịch vụ tra cứu gặp sự cố và nút sao chép nhanh kết quả.
- **Chọn model Gemini & tự động chuyển đổi khi hết quota**: Người dùng có thể chọn model ưu tiên ngay trên Side Panel. Khi một model chạm hạn mức (`429`), backend tự động đặt cooldown theo model trong process và xoay vòng sang model khả dụng tiếp theo, đồng thời trả về thông tin model thực tế đã dùng ở từng bước (`model_usage`).
- **Tách API key & Bảo mật**: Backend giữ toàn bộ API key của Gemini, Tavily và Fact Check. Extension giao tiếp với backend qua `X-API-Key` kết hợp giới hạn tốc độ (rate limiting theo IP, theo key và hạn mức toàn cục mỗi ngày).

## 🏗 Kiến trúc dự án (Architecture)

Dự án chia làm 2 phần chính (Client-Server):

1. **Extension (Frontend / Client)**
   - Viết bằng TypeScript strict, HTML/CSS và DOM thuần; build bằng Vite.
   - Thư mục: `extension/`
   - Tổ chức theo tính năng: `src/entrypoints/` khởi tạo các điểm chạy Manifest V3; `src/features/analysis/` chứa tính năng kiểm chứng; `src/infrastructure/` chứa HTTP/Storage; `src/shared/` chứa hợp đồng message và cấu hình.
   - Hướng dẫn tổ chức file, thêm tính năng và debug: [extension/README.md](extension/README.md).
   - Nhiệm vụ: Bắt sự kiện trên Facebook/Reddit (content script), truyền dữ liệu về background (service-worker) và hiển thị kết quả (side-panel).
2. **Backend API (Server)**
   - Viết bằng Python (FastAPI).
   - Thư mục: `backend/`
   - Nhiệm vụ: Xác thực và giới hạn lượt phân tích, dùng Gemini để trích xuất khẳng định, tra cứu Fact Check và Tavily song song, rồi đánh giá bằng chứng bằng Gemini.

Chi tiết về kiến trúc hệ thống vui lòng xem [ARCHITECTURE.md](ARCHITECTURE.md).

## 🚀 Hướng dẫn cài đặt & Chạy dự án (Getting Started)

### 1. Yêu cầu (Prerequisites)

- Node.js 20.19+ (nhánh 20), 22.13+ (nhánh 22) hoặc 24+ và `npm` để build extension.
- Python 3.11+ để chạy backend.
- Các API Keys cần thiết:
  - Gemini API Key
  - Tavily API Key
  - Google Fact Check Tools API Key

### 2. Cài đặt Backend

Di chuyển vào thư mục backend và thiết lập môi trường:

```bash
cd backend
python -m venv .venv

# Active môi trường ảo
# Trên Windows:
# .\.venv\Scripts\Activate.ps1
# Trên macOS/Linux:
source .venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt

# Tạo file .env dựa trên .env.example
cp .env.example .env  # PowerShell: Copy-Item .env.example .env
```

Cập nhật `backend/.env` với các API key của dịch vụ và đặt `EXTENSION_API_KEY` cho backend. Danh sách model, API và cách xử lý quota được mô tả trong [hướng dẫn backend](backend/README.md).

Để chạy backend (FastAPI):

```bash
uvicorn app.main:app --reload
```

Server chạy ở `http://127.0.0.1:8000`. Dùng `GET /health` để kiểm tra backend đã khởi động.

### 3. Cài đặt Extension

Mở terminal khác ở thư mục gốc dự án, sau đó cài extension:

```bash
cd extension
npm ci
cp .env.example .env  # PowerShell: Copy-Item .env.example .env
```

Đặt `VITE_EXTENSION_API_KEY` trong `extension/.env` bằng `EXTENSION_API_KEY` của backend. Chạy `npm run build` để tạo `extension/dist/` hoặc `npm run dev` để tự động build lại khi sửa mã.

### 4. Nạp Extension vào Chrome

1. Mở `chrome://extensions/` trên Chrome hoặc `edge://extensions/` trên Edge.
2. Bật **"Developer mode"** (Chế độ dành cho nhà phát triển).
3. Bấm **"Load unpacked"** (Tải tiện ích đã giải nén).
4. Chọn `extension/dist/`. Sao chép ID của tiện ích, đặt `ALLOWED_ORIGINS=chrome-extension://<extension-id>` trong `backend/.env` và khởi động lại backend.
5. Mở hoặc tải lại tab Facebook/Reddit, bôi đen một đoạn văn và bấm nút phân tích. Có thể dùng nút kiểm chứng bài viết ở trang chi tiết trên Reddit.

### 5. Kiểm thử & Kiểm tra chất lượng mã (Testing & Linting)

```bash
# Kiểm thử & lint Backend (từ thư mục backend/, đã bật .venv)
pytest
ruff check .

# Kiểm thử, typecheck & lint Extension (từ thư mục extension/)
npm test
npm run typecheck
npm run lint
```

## 📚 Roadmap & Tiến độ

Kiểm tra chi tiết tiến độ tại [ROADMAP.md](ROADMAP.md).

## 📝 Giấy phép (License)

Dự án được tạo ra nhằm mục đích học tập và nghiên cứu.
