/** Core passion/interest types for the Kindred matching system */

export interface PassionCategory {
  id: string;
  name: string;
  parentId: string | null;
  depth: number; // 0=root, 1=genre, 2=subgenre, 3=specific
}

export interface UserPassion {
  id: string;
  userId: string;
  categoryId: string;
  /** Category hierarchy path, e.g., "Music > Jazz > Bebop > Thelonious Monk" */
  path: string;
  /** Self-rated intensity 1-10 */
  selfRating: number;
  /** Behavioral intensity derived from activity (0-1) */
  behavioralScore: number;
  /** When this passion was last actively engaged with */
  lastEngaged: string;
  /** Decay-adjusted current intensity (computed) */
  currentIntensity: number;
  /** Free-text description of why this matters */
  story: string;
}

export interface PassionMatch {
  userId: string;
  displayName: string;
  sharedPassions: SharedPassion[];
  matchScore: number;
  distance: number | null; // miles, null if location not shared
}

export interface SharedPassion {
  categoryPath: string;
  depthMatch: number; // how specific the shared interest is (higher = better)
  yourIntensity: number;
  theirIntensity: number;
}

export interface OnboardingResponse {
  freeText: string;
  extractedPassions: ExtractedPassion[];
}

export interface ExtractedPassion {
  categoryPath: string;
  inferredIntensity: number;
  confidence: number;
  sourcePhrase: string;
}
