import type { Metadata } from "next";
import "./globals.css";
import "./operations.css";

export const metadata: Metadata = {
  title: "GRC Platform",
  description: "Sovereign, framework-agnostic GRC platform",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
