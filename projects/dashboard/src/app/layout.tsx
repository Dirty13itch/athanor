import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Space_Grotesk } from "next/font/google";
import { AppProviders } from "@/components/app-providers";
import { AppShell } from "@/components/app-shell";
import { RegisterSW } from "@/components/register-sw";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  variable: "--font-system",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const spaceGrotesk = Space_Grotesk({
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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${plexSans.variable} ${spaceGrotesk.variable} ${plexMono.variable} font-sans antialiased`}
      >
        <AppProviders>
          <RegisterSW />
          <AppShell>{children}</AppShell>
        </AppProviders>
      </body>
    </html>
  );
}
