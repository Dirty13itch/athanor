"use client";

export type JsonObject = Record<string, unknown>;

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export function asObject(value: unknown): JsonObject | null {
  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
    return value as JsonObject;
  }
  return null;
}

export function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

export function getString(value: unknown, fallback = "--") {
  return typeof value === "string" && value ? value : fallback;
}

export function getOptionalString(value: unknown) {
  return typeof value === "string" && value ? value : null;
}

export function getNumber(value: unknown, fallback = 0) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

export function getBoolean(value: unknown, fallback = false) {
  return typeof value === "boolean" ? value : fallback;
}

export function formatKey(value: string) {
  return value.replace(/[_-]/g, " ");
}
