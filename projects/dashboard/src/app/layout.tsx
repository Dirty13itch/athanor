import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, IBM_Plex_Sans_Condensed } from "next/font/google";
import { AppProviders } from "@/components/app-providers";
import { AppShell } from "@/components/app-shell";
import { RegisterSW } from "@/components/register-sw";
import { getOverviewSnapshot } from "@/lib/dashboard-data";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  variable: "--font-system",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const plexSansCondensed = IBM_Plex_Sans_Condensed({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-data",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: {
    default: "Athanor",
    template: "%s | Athanor",
  },
  description: "Homelab command center for services, GPU telemetry, models, and agents.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  let initialOverview = null;
  try {
    initialOverview = await getOverviewSnapshot();
  } catch {
    initialOverview = null;
  }

  return (
    <html lang="en" className="dark">
      <body
        className={`${plexSans.variable} ${plexSansCondensed.variable} ${plexMono.variable} font-sans antialiased`}
      >
        <AppProviders>
          <RegisterSW />
          <AppShell initialOverview={initialOverview}>{children}</AppShell>
        </AppProviders>
      </body>
    </html>
  );
}
