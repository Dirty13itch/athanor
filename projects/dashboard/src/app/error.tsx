"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ErrorPanel } from "@/components/error-panel";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="space-y-6">
      <ErrorPanel description={error.message || "Something went wrong while rendering the dashboard."} />
      <Button onClick={() => reset()}>Try again</Button>
    </div>
  );
}
