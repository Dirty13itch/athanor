"use client";

import { useImplicitFeedback } from "@/hooks/use-implicit-feedback";

export function ImplicitFeedbackTracker() {
  useImplicitFeedback();
  return null;
}
