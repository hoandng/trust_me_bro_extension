# TrustMeBro Extension

Hướng dẫn build Vite, nạp vào trình duyệt, gỡ lỗi và kiểm tra thủ công cho Chrome Extension Manifest V3 trong `extension/`.

Cập nhật: 19/11/2026.

## Cài đặt, cấu hình và kiến trúc

Xem yêu cầu Node.js, lệnh cài đặt và bảng biến môi trường tại [README.md](../README.md). Xem sơ đồ luồng dữ liệu, thành phần, quy tắc phụ thuộc và cách ly RAM/`chrome.storage` tại [ARCHITECTURE.md](../ARCHITECTURE.md).

## Build và lưu ý Manifest

Chạy từ thư mục `extension/`:

```bash
npm ci
npm run lint
npm run typecheck
npm test
npm run build      # Xuất ra extension/dist/ (hoặc npm run dev để watch)
```

`extension/vite.config.ts` sinh `dist/manifest.json` bằng plugin nội bộ và đọc `process.env.VITE_BACKEND_URL` trực tiếp (mặc định `http://127.0.0.1:8000/*`). Thay đổi `VITE_BACKEND_URL` chỉ trong `extension/.env` sẽ cập nhật URL gọi API ở `backend-client.ts` nhưng không đổi `host_permissions` trong `dist/manifest.json`; cần truyền biến môi trường `VITE_BACKEND_URL` có mẫu đường dẫn `/*` khi build cho origin khác và kiểm tra lại `dist/manifest.json`.

Artifact chính sau khi build:

- `dist/manifest.json`: cấu hình MV3 (`sidePanel`, `storage`, quyền host cho `facebook.com`, `reddit.com` và backend).
- `dist/background/index.js`: service worker dạng module.
- `dist/content-script/index.js`: content script nhúng vào Facebook và Reddit.
- `dist/src/entrypoints/sidepanel/index.html` và `dist/assets/`: giao diện và CSS/JS của Side Panel.

## Gỡ lỗi

| Hiện tượng                                  | Vị trí kiểm tra                                                                                            |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Không hiện nút nổi hoặc chọn sai vùng       | DevTools của trang → `selection-controller.ts`, `adapters/`, `floating-button.ts`                          |
| Không nhận yêu cầu hoặc không mở Side Panel | `chrome://extensions/` → Inspect service worker → `background.ts`, `handle-analysis.ts`                    |
| Lỗi HTTP hoặc sai định dạng kết quả         | Network của service worker → `backend-client.ts`, `analysis-api.ts`, `map-response.ts`                     |
| Bộ chọn model không tải khi mở Cài đặt      | Network của Side Panel → `GET /api/v1/models`, kiểm tra `VITE_BACKEND_URL`, `ALLOWED_ORIGINS`, `X-API-Key` |
| Trạng thái không cập nhật hoặc sai tab      | DevTools Side Panel → `controller.ts` và `chrome.storage.session` (`tabState_<tabId>`)                     |
| Lỗi hiển thị hoặc ký hiệu đánh dấu          | `render.ts`, `explanation-parser.ts`, `index.css`                                                          |

## Kiểm tra thủ công sau khi nạp `extension/dist/`

1. Mở `chrome://extensions/`, bật Developer mode, chọn **Load unpacked** tới `extension/dist/` (bấm Reload sau mỗi lần build và tải lại tab Facebook/Reddit).
2. Trên Facebook và Reddit: bôi đen đoạn văn 20–2000 ký tự, bấm nút nổi, xác nhận trạng thái `loading` 3 bước và kết quả trên Side Panel.
3. Trên trang chi tiết bài viết Reddit (`/comments/`): bấm nút **Kiểm chứng bài viết**.
4. Chuyển qua lại giữa hai tab: xác nhận trạng thái hiển thị riêng theo tab và mất khi tải lại/đóng tab.
5. Tắt backend để kiểm tra thông báo lỗi và nút **Thử lại**.
6. Mở mục **Cài đặt** trên Side Panel, kiểm tra danh sách model tải qua `GET /api/v1/models`, chọn model khác và xác nhận `model_usage` trong mục **Chi tiết kỹ thuật** ở lần phân tích tiếp theo.
7. Kiểm tra nút **Sao chép để chia sẻ** và xác nhận khung đánh giá 5 sao hiển thị thông báo tắt gửi mạng (`FEEDBACK_ENDPOINT_ENABLED = false`).
