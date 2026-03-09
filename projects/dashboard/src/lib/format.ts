export function formatLatency(value: number | null): string {
  if (value === null) {
    return "--";
  }

  if (value < 1000) {
    return `${value}ms`;
  }

  return `${(value / 1000).toFixed(1)}s`;
}

export function formatPercent(value: number | null, digits = 0): string {
  if (value === null || Number.isNaN(value)) {
    return "--";
  }

  return `${value.toFixed(digits)}%`;
}

export function formatMiB(value: string | number | null): string {
  if (value === null || value === undefined) {
    return "--";
  }

  const parsed = typeof value === "number" ? value : Number.parseFloat(value);
  if (Number.isNaN(parsed)) {
    return "--";
  }

  if (parsed >= 1024) {
    return `${(parsed / 1024).toFixed(1)} GiB`;
  }

  return `${parsed.toFixed(0)} MiB`;
}

export function formatWatts(value: string | number | null): string {
  if (value === null || value === undefined) {
    return "--";
  }

  const parsed = typeof value === "number" ? value : Number.parseFloat(value);
  if (Number.isNaN(parsed)) {
    return "--";
  }

  return `${parsed.toFixed(0)}W`;
}

export function average(values: number[]): number | null {
  if (values.length === 0) {
    return null;
  }

  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export function formatTimestamp(value: string | null): string {
  if (!value) {
    return "--";
  }

  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatRelativeTime(value: string | null): string {
  if (!value) {
    return "--";
  }

  const diffMs = Date.now() - new Date(value).getTime();
  const diffMinutes = Math.round(diffMs / 60000);
  if (Math.abs(diffMinutes) < 1) {
    return "just now";
  }

  if (Math.abs(diffMinutes) < 60) {
    return `${diffMinutes}m ago`;
  }

  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 24) {
    return `${diffHours}h ago`;
  }

  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
}

export function formatNumber(value: number | null, digits = 0): string {
  if (value === null || Number.isNaN(value)) {
    return "--";
  }

  return value.toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

export function formatCategoryLabel(value: string): string {
  return value
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function compactText(value: string, maxLength = 120): string {
  if (value.length <= maxLength) {
    return value;
  }

  return `${value.slice(0, maxLength - 1)}...`;
}
