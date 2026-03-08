import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ulrich Energy",
  description: "HERS Rating & Energy Audit Management",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Ulrich Energy",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  viewportFit: "cover",
  themeColor: "#0a0a0f",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen safe-area-top safe-area-bottom">
        <div className="flex min-h-screen flex-col">
          <Header />
          <main className="flex-1">{children}</main>
        </div>
      </body>
    </html>
  );
}

function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-[var(--color-border)] bg-[var(--color-bg)]/95 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <a href="/" className="flex items-center gap-2 text-lg font-semibold">
          <span className="text-[var(--color-primary)]">Ulrich</span>
          <span className="text-[var(--color-text-muted)]">Energy</span>
        </a>
        <nav className="flex items-center gap-1">
          <NavLink href="/inspections">Inspections</NavLink>
          <NavLink href="/reports">Reports</NavLink>
          <NavLink href="/clients">Clients</NavLink>
          <NavLink href="/analytics">Analytics</NavLink>
        </nav>
      </div>
    </header>
  );
}

function NavLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      className="rounded-md px-3 py-1.5 text-sm text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-elevated)] hover:text-[var(--color-text)]"
    >
      {children}
    </a>
  );
}
