import Link from "next/link";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";

export default function NotFound() {
  return (
    <EmptyState
      title="Route not found"
      description="The requested dashboard surface does not exist."
      action={
        <Button asChild>
          <Link href="/">Return to command center</Link>
        </Button>
      }
    />
  );
}
