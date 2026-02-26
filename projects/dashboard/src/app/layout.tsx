import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import { Inter, Cormorant_Garamond } from "next/font/google";
import { Geist_Mono } from "next/font/google";
import { SidebarNav } from "@/components/sidebar-nav";
import { BottomNav } from "@/components/bottom-nav";
import { CommandPalette } from "@/components/command-palette";
import { RegisterSW } from "@/components/register-sw";
import { LensProvider } from "@/hooks/use-lens";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const cormorant = Cormorant_Garamond({
  variable: "--font-cormorant",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Athanor",
  description: "Homelab command center — agents, GPUs, media, home automation",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Athanor",
  },
  formatDetection: {
    telephone: false,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
  themeColor: "#c8963c",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
      </head>
      <body
        className={`${inter.variable} ${cormorant.variable} ${geistMono.variable} font-sans antialiased`}
      >
        <Suspense>
          <LensProvider>
            <SidebarNav />
            <main className="min-h-screen p-4 pb-20 md:ml-56 md:p-6 md:pb-6">
              {children}
            </main>
            <BottomNav />
            <CommandPalette />
          </LensProvider>
        </Suspense>
        <RegisterSW />
      </body>
    </html>
  );
}
