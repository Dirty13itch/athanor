export const TIME_WINDOWS = [
  { id: "30m", label: "30m", minutes: 30 },
  { id: "3h", label: "3h", minutes: 180 },
  { id: "12h", label: "12h", minutes: 720 },
  { id: "24h", label: "24h", minutes: 1440 },
] as const;

export type TimeWindowId = (typeof TIME_WINDOWS)[number]["id"];

export function isTimeWindow(value: string | null | undefined): value is TimeWindowId {
  return TIME_WINDOWS.some((window) => window.id === value);
}

export function getTimeWindow(value: string | null | undefined) {
  return TIME_WINDOWS.find((window) => window.id === value) ?? TIME_WINDOWS[1];
}

export function getWindowSeconds(value: string | null | undefined): number {
  return getTimeWindow(value).minutes * 60;
}

export function getRangeStepSeconds(value: string | null | undefined): number {
  const minutes = getTimeWindow(value).minutes;
  if (minutes <= 30) {
    return 60;
  }

  if (minutes <= 180) {
    return 5 * 60;
  }

  return 15 * 60;
}
