import { cn } from "@/lib/utils";

export function Kbd({ className, children }: React.ComponentProps<"kbd">) {
  return (
    <kbd
      className={cn(
        "inline-flex min-w-6 items-center justify-center rounded-md border border-border/80 bg-background/70 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground",
        className
      )}
    >
      {children}
    </kbd>
  );
}
