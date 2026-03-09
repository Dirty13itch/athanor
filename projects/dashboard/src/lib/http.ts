import { ZodSchema } from "zod";

export async function fetchJson<T>(
  input: RequestInfo | URL,
  init: RequestInit | undefined,
  schema: ZodSchema<T>
): Promise<T> {
  const response = await fetch(input, init);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }

  const json = await response.json();
  return schema.parse(json);
}
