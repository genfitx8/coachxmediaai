import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CoachX Media AI",
  description: "AI-powered media coaching platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-gray-50 text-gray-900 font-sans">{children}</body>
    </html>
  );
}
