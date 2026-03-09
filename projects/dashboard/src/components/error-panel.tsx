import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

export function ErrorPanel({
  title = "Something went wrong",
  description,
  className,
}: {
  title?: string;
  description: string;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={cn("rounded-2xl border border-red-500/20 bg-red-500/5 p-4", className)}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-full bg-red-500/10 p-2 text-red-300">
          <AlertTriangle className="h-4 w-4" />
        </div>
        <div>
          <p className="font-medium text-red-100">{title}</p>
          <p className="mt-1 text-sm text-red-100/70">{description}</p>
        </div>
      </div>
    </div>
  );
}
