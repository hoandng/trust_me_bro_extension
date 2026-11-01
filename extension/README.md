# Fact Check Extension

Chrome Extension Manifest V3 dùng TypeScript strict, HTML/CSS và DOM thuần, build bằng Vite. Extension hỗ trợ chọn văn bản trên Facebook/Reddit và có nút kiểm chứng trong trang chi tiết bài viết Reddit.

## Chạy và kiểm tra

Từ thư mục `extension/`:

```bash
npm ci
npm run dev        # build lại khi source thay đổi
npm run typecheck
npm run lint
npm test           # API và Chrome Storage được mock; không gọi dịch vụ thật
npm run build
```

Dùng Node.js đáp ứng yêu cầu của Vite/ESLint trong lockfile (Node 22.13+ hoặc Node 24+). Sao chép `.env.example` thành `.env` và cấu hình backend nếu cần. Không đưa API key Gemini/Tavily/Google Fact Check vào extension.

**Tương thích toolchain:** TypeScript dùng dải `~6.0.3`, phù hợp với yêu cầu `>=4.8.4 <6.1.0` của `typescript-eslint` hiện tại. Giữ `package.json` và `package-lock.json` đồng bộ; cài bằng `npm ci`. Khi nâng TypeScript lên phiên bản minor/major mới, kiểm tra peer dependency của ESLint trước khi cập nhật.

Nạp extension: mở `chrome://extensions`, bật Developer mode, chọn **Load unpacked** và thư mục `extension/dist/`. Sau mỗi lần build, bấm Reload extension; tải lại tab Facebook/Reddit để cập nhật content script.

## Kiến trúc và trách nhiệm

Dùng **feature-based modular architecture**, kết hợp các điểm chạy độc lập của Manifest V3:

```text
src/
├── entrypoints/
│   ├── background.ts
│   ├── content.ts
│   └── sidepanel/
│       ├── index.html
│       └── index.ts
├── features/
│   └── analysis/
│       ├── types.ts
│       ├── state-store.ts
│       ├── background/
│       │   ├── handle-analysis.ts
│       │   ├── analysis-api.ts
│       │   └── map-response.ts
│       ├── content/
│       │   ├── selection-controller.ts
│       │   ├── adapters/
│       │   └── ui/
│       └── sidepanel/
│           ├── controller.ts
│           ├── render.ts
│           └── index.css
├── infrastructure/
│   ├── api/backend-client.ts
│   └── storage/session-store.ts
└── shared/
    ├── messages.ts
    └── config.ts
```

| Vị trí | Trách nhiệm |
|---|---|
| `entrypoints/` | Đăng ký listener, khởi tạo tính năng và gắn trang side panel vào bundle |
| `features/analysis/types.ts` | Kiểu request, response backend, dữ liệu UI và trạng thái phân tích |
| `features/analysis/background/` | Điều phối yêu cầu, chọn endpoint, chuyển dữ liệu backend sang UI |
| `features/analysis/state-store.ts` | Quy ước khóa `tabState_<tabId>` và subscription của tính năng |
| `features/analysis/content/` | Theo dõi lựa chọn, adapter nền tảng, nút nổi/nút bài viết |
| `features/analysis/sidepanel/controller.ts` | Đổi tab, theo dõi trạng thái, yêu cầu retry |
| `features/analysis/sidepanel/render.ts` | Render DOM, loading, nguồn và sao chép kết quả |
| `infrastructure/` | HTTP, xác thực backend, timeout và adapter Chrome Storage |
| `shared/` | Hợp đồng message, kiểm tra message đầu vào và cấu hình chung |

Luồng phụ thuộc là `entrypoints → features → infrastructure`. Tính năng có thể dùng `shared`; `shared/messages.ts` chỉ import type dữ liệu tính năng, không import mã chạy của tính năng. Dùng `import type` cho kiểu dữ liệu.

Không import `entrypoints/` từ module khác. Giữ mã DOM trong content/side panel, mã gọi backend trong background. Module dùng ở nhiều ngữ cảnh của cùng tính năng đặt ở gốc tính năng, như `analysis/state-store.ts`. Hạ tầng không import tính năng. Chỉ đưa mã thực sự dùng chung vào `shared/` hoặc `infrastructure/`.

## Luồng xử lý và build

```text
Content/adapter → ANALYZE_REQUEST → background handler → analysis API → FastAPI
                                         │                    │
                                         └─ loading/success/error
                                                   │
                                      chrome.storage.session
                                                   │
                                      side panel controller → render
```

Background mở side panel ngay khi nhận message; handler lưu request để retry, map response và ghi trạng thái theo tab. Side panel chỉ theo dõi tab đang được chọn. Trạng thái lưu trong `chrome.storage.session` để giữ qua các lần service worker dừng/chạy lại; đây chưa phải cache kết quả.

`vite.config.ts` tạo `dist/manifest.json` bằng plugin nội bộ. Đường dẫn side panel lấy từ `src/shared/config.ts`, dùng chung cho manifest và background. Các artifact chính:

- `dist/background/index.js`: service worker dạng module.
- `dist/content-script/index.js`: content script không có import/export ESM ở cấp cao nhất.
- `dist/src/entrypoints/sidepanel/index.html`: trang side panel.
- `dist/assets/`: CSS, mã side panel và các module dùng chung được bundler tạo.

## Thêm tính năng và service

**Thêm mạng xã hội:** tạo adapter trong `features/analysis/content/adapters/`, implement `PlatformAdapter`, đăng ký tại `adapters/index.ts`, cập nhật `matches`, `host_permissions` và `web_accessible_resources` trong Vite. Giữ logic đặc thù DOM của nền tảng trong adapter.

**Thêm tóm tắt bài báo:** tạo `features/article-summary/` với `types.ts`, `content/article-extractor.ts`, `background/` và `sidepanel/`. Bổ sung message trong `shared/messages.ts`, nối handler/controller tại entrypoint và thêm endpoint backend. Dùng HTTP client chung; định nghĩa request/response và mapper riêng cho tóm tắt. Nếu cần đọc website ngoài Facebook/Reddit, bổ sung quyền truy cập phù hợp.

**Thêm cache:** tạo `infrastructure/cache/` để triển khai get/set/delete, TTL và giới hạn số lượng/dung lượng. Mỗi tính năng tự quyết định key gồm loại tác vụ, hash nội dung, tùy chọn và phiên bản xử lý. Handler tra cache trước khi gọi API và chỉ lưu kết quả phù hợp. Tách cache khỏi `tabState_<tabId>`; hỗ trợ bỏ qua cache khi retry/cập nhật kết quả. Chọn session hoặc local theo yêu cầu giữ dữ liệu. Chưa có cache trong source hiện tại.

**Thêm service AI/search:** tích hợp ở `backend/app/services/`; API key bên ngoài và logic AI nằm ở backend. Extension chỉ thay đổi khi cần tính năng hoặc hợp đồng API mới.

## Debug

| Vấn đề | Kiểm tra |
|---|---|
| Không hiện nút/chọn sai nội dung | DevTools của trang → selection controller, adapter và floating button |
| Không nhận yêu cầu/không mở panel | `chrome://extensions` → Inspect service worker → entrypoint và `handle-analysis.ts` |
| Request lỗi hoặc kết quả sai định dạng | Network của service worker → `backend-client.ts`, `analysis-api.ts`, `map-response.ts` |
| UI không cập nhật hoặc lẫn tab | DevTools side panel → controller; kiểm tra `tabState_<tabId>` trong extension storage |
| UI hiển thị sai | `render.ts` và `index.css`; dùng `textContent` với dữ liệu bên ngoài |

Log chỉ ghi metadata như nền tảng, độ dài văn bản và trạng thái. Không log nội dung bài đăng, request body hoặc API key.

## Xác minh

`npm test` dùng Node test runner và Vite đã có sẵn để chạy TypeScript. Build test chỉ dùng cấu hình giả, không đọc `.env`; artifact nằm trong `.cache/tests/`. Test kiểm tra hợp đồng message, mapping response, subscription/trạng thái độc lập giữa các tab và luồng loading → success/error khi gọi API mock.

Kiểm tra thủ công sau khi reload extension:

1. Facebook/Reddit: chọn văn bản 20–2000 ký tự, bấm nút, kiểm tra loading và kết quả.
2. Reddit: vào trang chi tiết bài viết và kiểm tra nút kiểm chứng nội dung bài.
3. Đổi qua lại hai tab: nội dung và kết quả hiển thị riêng theo tab.
4. Tắt backend hoặc tạo lỗi API: kiểm tra thông báo lỗi và nút Thử lại.
5. Kiểm tra Xem thêm/Thu gọn, link nguồn, thanh confidence và Sao chép kết quả.
6. Nếu Chrome chặn mở panel từ message, badge `!` xuất hiện; bấm icon extension để mở panel.
