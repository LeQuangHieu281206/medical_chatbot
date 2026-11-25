# Giao diện Next.js — Trợ lý Y tế

Giao diện chat cho chatbot y tế, dùng **Next.js 16 (App Router) + TypeScript + Tailwind CSS 4**.
Hệ thống thiết kế lấy từ [DESIGN-claude.md](../DESIGN-claude.md): nền kem ấm, chữ serif
cho tiêu đề, CTA coral và bề mặt tối cho các điểm nhấn.

## Chạy

Cần backend Python (FastAPI bridge) ở terminal khác:

```bash
# Từ thư mục gốc repo
source .venv/bin/activate
uvicorn app.api.server:app --host 127.0.0.1 --port 8000
```

Sau đó:

```bash
cd web
npm install
npm run dev          # http://localhost:3000
```

Biến môi trường tuỳ chọn: `MEDBOT_API_URL` (mặc định `http://127.0.0.1:8000`).
Xem `.env.example`.

## Cấu trúc

```
src/
  app/
    layout.tsx              # font, metadata, <html lang="vi">
    page.tsx                # render ChatApp
    globals.css             # design tokens + base styles
    api/chat/route.ts       # proxy SSE sang FastAPI, giữ API key/URL ở server
  components/
    chat/
      chat-app.tsx          # bố cục, cuộn, điều phối trạng thái
      chat-sidebar.tsx      # lịch sử, cuộc trò chuyện mới, chế độ kỹ thuật
      chat-header.tsx
      empty-state.tsx       # màn hình bắt đầu + câu hỏi gợi ý
      message-bubble.tsx    # tin nhắn, markdown, thực thể, nguồn
      source-list.tsx
      entity-chips.tsx
      composer.tsx          # ô nhập, Enter/Shift+Enter, nút dừng
    ui/brand-mark.tsx
  hooks/
    use-chat.ts             # gửi câu hỏi, stream, dừng, chọn/xoá hội thoại
  lib/
    chat-stream.ts          # đọc SSE
    chat-store.ts           # lưu hội thoại vào localStorage
    types.ts
    suggestions.ts
    cn.ts
```

## Ghi chú

- Hội thoại lưu trong `localStorage` của trình duyệt; không gửi lên dịch vụ ngoài.
- `/api/chat` chỉ chuyển tiếp SSE. Nếu backend chưa chạy, giao diện hiện lỗi rõ ràng.
- Chạy `npm run lint` và `npm run build` trước khi phát hành.
