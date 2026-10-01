import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PPT AX",
  description: "인트윈 제안 자동화 플랫폼",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
