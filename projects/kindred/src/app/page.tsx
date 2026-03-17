import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold tracking-tight">Kindred</h1>
      <p className="mt-4 max-w-md text-center text-lg text-gray-600">
        Find your people through shared passions. Not demographics, not
        algorithms — the things you actually care about.
      </p>
      <div className="mt-8 flex gap-4">
        <Link
          href="/onboarding"
          className="rounded-lg bg-indigo-600 px-6 py-3 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Get Started
        </Link>
        <Link
          href="/explore"
          className="rounded-lg border border-gray-300 px-6 py-3 text-sm font-medium hover:bg-gray-50"
        >
          Explore
        </Link>
      </div>
    </main>
  );
}
