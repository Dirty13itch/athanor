/** User profile types */

export interface User {
  id: string;
  displayName: string;
  bio: string;
  location: { lat: number; lng: number } | null;
  city: string | null;
  createdAt: string;
  onboardingComplete: boolean;
  passionCount: number;
}

export interface UserProfile extends User {
  passions: import("./passion").UserPassion[];
  topMatches: import("./passion").PassionMatch[];
}
