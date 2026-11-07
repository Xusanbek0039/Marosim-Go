"use client";

import { useCallback, useMemo, useState } from "react";

import type { ListParams } from "@/lib/api/types";

/** Page / search / filters / ordering state for a list screen. Any change resets to page 1. */
export function useListState(initial: { ordering: string; pageSize?: number }) {
  const [page, setPage] = useState(1);
  const [search, setSearchRaw] = useState("");
  const [ordering, setOrderingRaw] = useState(initial.ordering);
  const [filters, setFilters] = useState<Record<string, string | undefined>>({});
  const pageSize = initial.pageSize ?? 10;

  const setSearch = useCallback((value: string) => {
    setSearchRaw(value);
    setPage(1);
  }, []);
  const setOrdering = useCallback((value: string) => {
    setOrderingRaw(value);
    setPage(1);
  }, []);
  const setFilter = useCallback((key: string, value: string | undefined) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  }, []);

  const params: ListParams = useMemo(
    () => ({ page, page_size: pageSize, search: search || undefined, ordering, ...filters }),
    [page, pageSize, search, ordering, filters],
  );
  const hasQuery = Boolean(search) || Object.values(filters).some(Boolean);

  return { params, page, setPage, search, setSearch, ordering, setOrdering, filters, setFilter, pageSize, hasQuery };
}

export const STATUS_FILTER = {
  key: "is_active",
  label: "Holat",
  options: [
    { value: "true", label: "Faol" },
    { value: "false", label: "Nofaol" },
  ],
};
