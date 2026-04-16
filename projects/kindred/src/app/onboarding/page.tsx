"use client";

import { useState } from "react";

interface ExtractedPassion {
  categoryPath: string;
  inferredIntensity: number;
  confidence: number;
  sourcePhrase: string;
}

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [responses, setResponses] = useState<string[]>([]);
  const [current, setCurrent] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [passions, setPassions] = useState<ExtractedPassion[]>([]);
  const [error, setError] = useState<string | null>(null);

  const prompts = [
    "What could you talk about for hours without getting bored?",
    "What's something you've spent way too much time learning about?",
    "If you had a free weekend with no obligations, what would you actually do?",
    "What's a niche interest most people don't know you have?",
    "What topic makes you light up when someone mentions it?",
  ];

  function handleNext() {
    if (!current.trim()) return;
    const allResponses = [...responses, current];
    setResponses(allResponses);
    setCurrent("");
    if (step < prompts.length - 1) {
      setStep(step + 1);
    } else {
      setStep(prompts.length);
      extractPassions(allResponses);
    }
  }

  async function extractPassions(allResponses: string[]) {
    setExtracting(true);
    setError(null);
    try {
      const resp = await fetch("/api/passions/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ responses: allResponses }),
      });
      const data = await resp.json();
      if (data.passions) {
        setPassions(data.passions);
      } else {
        setError(data.error ?? "Extraction failed");
      }
    } catch {
      setError("Network error");
    } finally {
      setExtracting(false);
    }
  }

  // Results screen
  if (step >= prompts.length) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center p-8">
        <div className="w-full max-w-lg">
          <h1 className="text-2xl font-bold">
            {extracting ? "Analyzing your passions..." : "Your Passion Map"}
          </h1>

          {extracting && (
            <div className="mt-6 space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-12 animate-pulse rounded-lg bg-gray-100" />
              ))}
            </div>
          )}

          {error && (
            <p className="mt-4 text-sm text-red-600">{error}</p>
          )}

          {passions.length > 0 && (
            <div className="mt-6 space-y-3">
              {passions
                .sort((a, b) => b.inferredIntensity - a.inferredIntensity)
                .map((p, i) => {
                  const parts = p.categoryPath.split("/");
                  const depth = parts.length;
                  return (
                    <div
                      key={i}
                      className="rounded-lg border border-gray-200 bg-white p-4"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium">
                            {parts.map((part, j) => (
                              <span key={j}>
                                {j > 0 && (
                                  <span className="mx-1 text-gray-300">/</span>
                                )}
                                <span
                                  className={
                                    j === parts.length - 1
                                      ? "text-indigo-600 font-semibold"
                                      : "text-gray-500"
                                  }
                                >
                                  {part}
                                </span>
                              </span>
                            ))}
                          </p>
                          <p className="mt-1 text-xs text-gray-400 italic">
                            &ldquo;{p.sourcePhrase}&rdquo;
                          </p>
                        </div>
                        <div className="text-right">
                          <div className="flex items-center gap-1">
                            {Array.from({ length: 5 }).map((_, s) => (
                              <div
                                key={s}
                                className={`h-2 w-2 rounded-full ${
                                  s < Math.round(p.inferredIntensity * 5)
                                    ? "bg-indigo-500"
                                    : "bg-gray-200"
                                }`}
                              />
                            ))}
                          </div>
                          <p className="mt-1 text-[10px] text-gray-400">
                            depth {depth} | conf {Math.round(p.confidence * 100)}%
                          </p>
                        </div>
                      </div>
                      {/* Depth indicator */}
                      <div className="mt-2 h-1 rounded-full bg-gray-100">
                        <div
                          className="h-full rounded-full bg-indigo-500 transition-all"
                          style={{ width: `${Math.min(depth * 25, 100)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}

              <button
                className="mt-4 w-full rounded-lg bg-indigo-600 px-6 py-3 text-sm font-medium text-white hover:bg-indigo-700"
                onClick={() => {
                  // TODO: Store profile and navigate to explore/matches
                  window.location.href = "/explore";
                }}
              >
                Find My People ({passions.length} passions mapped)
              </button>
            </div>
          )}

          {/* Source responses */}
          <details className="mt-6">
            <summary className="cursor-pointer text-xs text-gray-400">
              Your responses
            </summary>
            <div className="mt-2 space-y-2 text-sm text-gray-500">
              {responses.map((r, i) => (
                <p key={i} className="rounded bg-gray-50 p-3 italic">
                  &ldquo;{r}&rdquo;
                </p>
              ))}
            </div>
          </details>
        </div>
      </main>
    );
  }

  // Question screen
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="w-full max-w-lg">
        <div className="mb-8">
          <div className="flex gap-1">
            {prompts.map((_, i) => (
              <div
                key={i}
                className={`h-1 flex-1 rounded-full ${i <= step ? "bg-indigo-600" : "bg-gray-200"}`}
              />
            ))}
          </div>
          <p className="mt-2 text-xs text-gray-400">
            {step + 1} of {prompts.length}
          </p>
        </div>

        <h2 className="text-xl font-semibold">{prompts[step]}</h2>

        <textarea
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          placeholder="Tell us more..."
          rows={4}
          className="mt-4 w-full rounded-lg border border-gray-300 p-4 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
        />

        <button
          onClick={handleNext}
          disabled={!current.trim()}
          className="mt-4 w-full rounded-lg bg-indigo-600 px-6 py-3 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {step < prompts.length - 1 ? "Next" : "Find My People"}
        </button>
      </div>
    </main>
  );
}
