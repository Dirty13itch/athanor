"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[oklch(0.07_0_0)] text-[oklch(0.93_0.005_60)] flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4">
          <h1 className="text-xl font-semibold">Something went wrong</h1>
          <p className="text-sm text-[oklch(0.55_0.01_60)]">{error.message}</p>
          <button
            onClick={reset}
            className="px-4 py-2 text-sm rounded-md bg-[oklch(0.75_0.08_65)] text-[oklch(0.07_0_0)] hover:opacity-90"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
