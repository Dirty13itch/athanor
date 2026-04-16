import { Check, Wrench, X } from "lucide-react";

type RatingStatus = "approved" | "flagged" | "rejected" | null;

export function RatingBadge({ status }: { status: RatingStatus }) {
  if (!status) return null;

  const map = {
    approved: { Icon: Check, bg: "bg-emerald-500/80" },
    flagged: { Icon: Wrench, bg: "bg-amber-500/80" },
    rejected: { Icon: X, bg: "bg-red-500/80" },
  } as const;

  const { Icon, bg } = map[status];

  return (
    <div className={`absolute right-2 top-2 rounded-full p-1 ${bg} bg-black/70`}>
      <Icon className="h-3 w-3 text-white" />
    </div>
  );
}
