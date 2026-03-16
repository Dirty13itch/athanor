"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Bot,
  Cpu,
  LayoutDashboard,
  Menu,
  MessageSquare,
  Network,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/gpu", label: "GPU Metrics", icon: Cpu },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/services", label: "Services", icon: Activity },
  { href: "/topology", label: "Topology", icon: Network },
];

function NavLinks({
  pathname,
  mobile = false,
}: {
  pathname: string;
  mobile?: boolean;
}) {
  return (
    <nav className="space-y-1 p-2">
      {navItems.map((item) => {
        const active = pathname === item.href;
        const link = (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            )}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </Link>
        );

        if (!mobile) {
          return link;
        }

        return (
          <SheetClose asChild key={item.href}>
            {link}
          </SheetClose>
        );
      })}
    </nav>
  );
}

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-40 border-b border-border/80 bg-background/90 backdrop-blur lg:hidden">
        <div className="flex h-16 items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-3 text-foreground">
            <div className="h-2 w-2 rounded-full bg-primary shadow-[0_0_22px_color-mix(in_oklab,var(--accent-structural)_40%,transparent)]" />
            <div>
              <p className="font-heading text-xl font-semibold tracking-wide">Athanor</p>
              <p className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">
                Command Center
              </p>
            </div>
          </Link>

          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Open navigation">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>

            <SheetContent
              side="left"
              className="surface-sidebar w-[18rem] border-r p-0 backdrop-blur-xl"
              showCloseButton={false}
            >
              <SheetHeader className="border-b border-border/80 px-4 py-4 text-left">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <SheetTitle className="font-heading text-xl tracking-wide">Athanor</SheetTitle>
                    <SheetDescription>Homelab command center</SheetDescription>
                  </div>

                  <SheetClose asChild>
                    <Button variant="ghost" size="icon" aria-label="Close navigation">
                      <X className="h-4 w-4" />
                    </Button>
                  </SheetClose>
                </div>
              </SheetHeader>

              <NavLinks pathname={pathname} mobile />

              <div className="mt-auto border-t border-border/80 p-4 text-xs text-muted-foreground">
                Live views for models, services, telemetry, and agents.
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </header>

      <aside className="surface-sidebar fixed inset-y-0 left-0 hidden w-56 flex-col border-r backdrop-blur-xl lg:flex">
        <div className="flex h-16 items-center border-b border-border/80 px-4">
          <Link href="/" className="text-foreground">
            <p className="font-heading text-2xl font-semibold tracking-wide">Athanor</p>
            <p className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">
              Command Center
            </p>
          </Link>
        </div>

        <div className="flex-1 py-2">
          <NavLinks pathname={pathname} />
        </div>

        <div className="border-t border-border/80 p-4 text-xs text-muted-foreground">
          Homelab telemetry, services, and agent control.
        </div>
      </aside>
    </>
  );
}
