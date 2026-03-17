"use client";

import { useState } from "react";

/**
 * Onboarding flow — maps passion depth through interactive questions.
 * "Tell me about something you could talk about for hours"
 * NLP extracts passion signals from free-text responses.
 */
export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [responses, setResponses] = useState<string[]>([]);
  const [current, setCurrent] = useState("");

  const prompts = [
    "What could you talk about for hours without getting bored?",
    "What's something you've spent way too much time learning about?",
    "If you had a free weekend with no obligations, what would you actually do?",
    "What's a niche interest most people don't know you have?",
    "What topic makes you light up when someone mentions it?",
  ];

  function handleNext() {
    if (!current.trim()) return;
    setResponses([...responses, current]);
    setCurrent("");
    if (step < prompts.length - 1) {
      setStep(step + 1);
    } else {
      // TODO: Submit to /api/passions/extract for NLP processing
      // For now, just show completion
      setStep(prompts.length);
    }
  }

  if (step >= prompts.length) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center p-8">
        <h1 className="text-2xl font-bold">Your passions are being analyzed...</h1>
        <p className="mt-4 text-gray-600">
          We&apos;re using AI to understand the depth and specificity of your interests.
        </p>
        <div className="mt-6 space-y-2 text-sm text-gray-500">
          {responses.map((r, i) => (
            <p key={i} className="rounded bg-gray-50 p-3 italic">&ldquo;{r}&rdquo;</p>
          ))}
        </div>
      </main>
    );
  }

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
