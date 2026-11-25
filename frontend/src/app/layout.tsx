import type { Metadata } from "next";
import { Inter, Source_Serif_4 } from "next/font/google";
import "./globals.css";

const sans = Inter({
  variable: "--font-sans-face",
  subsets: ["latin", "vietnamese"],
  display: "swap",
});

const display = Source_Serif_4({
  variable: "--font-display-face",
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Trợ lý Y tế — Tư vấn sức khoẻ",
  description:
    "Chatbot tư vấn sức khoẻ tiếng Việt chạy hoàn toàn trên máy của bạn. Thông tin chỉ mang tính tham khảo, không thay thế bác sĩ.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="vi" className={`${sans.variable} ${display.variable} h-full`}>
      <body className="min-h-full bg-canvas text-body">{children}</body>
    </html>
  );
}
