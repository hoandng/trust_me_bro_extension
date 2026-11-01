# Trust Me Bro Extension

Dự án này là một **Browser Extension (Trình mở rộng trình duyệt)** hỗ trợ kiểm tra độ tin cậy của nội dung trên mạng xã hội. Extension cho phép người dùng chọn một đoạn văn bản trên Facebook hoặc Reddit và nhận được phân tích, đánh giá, kèm theo các nguồn tham khảo liên quan về tính xác thực của thông tin đó.

## 🌟 Tính năng (Features)

- **Phân tích bôi đen**: Bôi đen một đoạn văn bản trên Facebook hoặc Reddit, một nút "Phân tích" sẽ hiện ra.
- **Orchestrator Backend**: Một backend mạnh mẽ viết bằng FastAPI đóng vai trò điều phối nhiều nguồn xác thực:
  - **Gemini API**: Phân tích, tổng hợp thông tin, sinh ra kết luận cuối cùng (Verdict) với điểm số tin cậy (Confidence score).
  - **Google Fact Check Tools API**: Tìm kiếm những tuyên bố (claims) đã được xác minh trước đó bởi các tổ chức uy tín.
  - **Tavily API**: Tìm kiếm thời gian thực để thu thập các nguồn tin tức và bài viết có liên quan.
- **Side Panel UI**: Hiển thị kết quả kiểm chứng chi tiết, trực quan bao gồm mức độ tin cậy, giải thích lý do, và các đường dẫn nguồn.
- **An toàn & Bảo mật**: API keys và logic đánh giá được bảo vệ an toàn trên backend, client (extension) chỉ đảm nhiệm việc hiển thị và tương tác người dùng.

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
   - Nhiệm vụ: Xử lý rate limiting, nhận request từ extension, gọi song song các dịch vụ AI/fact-check, và tổng hợp đánh giá gửi lại cho client.

Chi tiết về kiến trúc hệ thống vui lòng xem [ARCHITECTURE.md](ARCHITECTURE.md).

## 🚀 Hướng dẫn cài đặt & Chạy dự án (Getting Started)

### 1. Yêu cầu (Prerequisites)

- [Node.js](https://nodejs.org/) (>= 18) và `npm` hoặc `yarn` để chạy extension.
- [Python](https://www.python.org/) (>= 3.10) để chạy backend.
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
.venv\Scripts\activate
# Trên macOS/Linux:
source .venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt

# Tạo file .env dựa trên .env.example
cp .env.example .env
```

Cập nhật file `.env` với các API keys của bạn.

Để chạy backend (FastAPI):

```bash
uvicorn app.main:app --reload
```

Server sẽ chạy ở `http://localhost:8000`.

### 3. Cài đặt Extension

Di chuyển vào thư mục extension và cài đặt:

```bash
cd extension
npm install

# Build dự án (chế độ watch để tự động build khi đổi code)
npm run build -- --watch
```

Sau khi build, mã nguồn extension đã biên dịch sẽ nằm trong thư mục `extension/dist/`.

### 4. Nạp Extension vào Chrome

1. Mở trình duyệt Chrome/Edge, vào đường dẫn `chrome://extensions/`
2. Bật **"Developer mode"** (Chế độ dành cho nhà phát triển).
3. Bấm **"Load unpacked"** (Tải tiện ích đã giải nén).
4. Chọn thư mục `dist` trong dự án của bạn (`factcheck-project-2/extension/dist`).

## 📚 Roadmap & Tiến độ

Kiểm tra chi tiết tiến độ tại [ROADMAP.md](ROADMAP.md).

## 📝 Giấy phép (License)

Dự án được tạo ra nhằm mục đích học tập và nghiên cứu.
