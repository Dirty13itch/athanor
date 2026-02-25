import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Empire of Broken Queens",
  description: "AI-driven interactive cinematic game",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
