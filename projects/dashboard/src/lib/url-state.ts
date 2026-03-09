"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

export function useUrlState() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  function setSearchValue(key: string, value: string | null) {
    const next = new URLSearchParams(searchParams.toString());

    if (!value) {
      next.delete(key);
    } else {
      next.set(key, value);
    }

    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }

  function setSearchValues(values: Record<string, string | null | undefined>) {
    const next = new URLSearchParams(searchParams.toString());

    for (const [key, value] of Object.entries(values)) {
      if (!value) {
        next.delete(key);
      } else {
        next.set(key, value);
      }
    }

    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }

  function getSearchValue(key: string, fallback: string) {
    return searchParams.get(key) ?? fallback;
  }

  return {
    pathname,
    searchParams,
    getSearchValue,
    setSearchValue,
    setSearchValues,
  };
}
