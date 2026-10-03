import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "Luma · AI Study Assistant", description: "Demo frontend trợ lý học tập: tài liệu, AI Tutor, flashcard, quiz và sơ đồ tư duy." };
export default function RootLayout({children}:{children:React.ReactNode}) {
  return <html lang="vi"><body>{children}</body></html>;
}
