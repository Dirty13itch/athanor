"use client";

export default function OfflinePage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <div className="text-6xl">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="mx-auto h-16 w-16 text-muted-foreground">
          <path d="M12.01 21.49" />
          <path d="M7.5 19.1a3.5 3.5 0 0 1 2-1 4 4 0 0 1 1-.1 3.5 3.5 0 0 1 3.5 2.1" />
          <path d="M2 8.82a15.06 15.06 0 0 1 4.5-2.87" />
          <path d="M17.14 6.07A14.9 14.9 0 0 1 22 8.82" />
          <path d="M6.53 12.48a8 8 0 0 1 2-1.47" />
          <path d="M14.87 11.2a8 8 0 0 1 2.67 1.38" />
          <line x1="2" x2="22" y1="2" y2="22" />
        </svg>
      </div>
      <h1 className="font-heading text-2xl font-semibold text-foreground">
        You&apos;re offline
      </h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        Athanor needs a network connection to reach your homelab.
        Check your connection and try again.
      </p>
      <button
        onClick={() => window.location.reload()}
        className="mt-4 rounded-md bg-primary px-6 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
      >
        Retry
      </button>
    </div>
  );
}
