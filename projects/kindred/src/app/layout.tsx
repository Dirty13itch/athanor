import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "Kindred",
  description: "Find your people through shared passions",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
