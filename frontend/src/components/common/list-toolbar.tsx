"use client";

import { SearchIcon, XIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export interface FilterDef {
  key: string;
  label: string;
  options: { value: string; label: string }[];
}

interface ListToolbarProps {
  search: string;
  onSearch: (value: string) => void;
  placeholder: string;
  filters?: FilterDef[];
  values: Record<string, string | undefined>;
  onFilter: (key: string, value: string | undefined) => void;
  ordering?: { value: string; options: { value: string; label: string }[]; onChange: (v: string) => void };
}

const ALL = "__all__";

/** Debounced search + filter selects + ordering. Shared by every list page. */
export function ListToolbar({ search, onSearch, placeholder, filters = [], values, onFilter, ordering }: ListToolbarProps) {
  const [draft, setDraft] = useState(search);

  useEffect(() => {
    const id = setTimeout(() => {
      if (draft !== search) onSearch(draft.trim());
    }, 350);
    return () => clearTimeout(id);
  }, [draft, search, onSearch]);

  return (
    <div className="flex flex-wrap items-center gap-2.5">
      <label className="relative flex min-w-[240px] flex-[1_1_280px] items-center">
        <span className="sr-only">{placeholder}</span>
        <SearchIcon className="pointer-events-none absolute left-3.5 size-4 text-muted-foreground" aria-hidden />
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={placeholder}
          className="h-11 w-full rounded-xl border border-input bg-white/60 pr-10 pl-10 text-sm outline-none transition placeholder:text-muted-foreground focus-visible:border-brand focus-visible:ring-4 focus-visible:ring-brand/20 dark:bg-slate-950/40 dark:focus-visible:border-cyan-400/70"
        />
        {draft && (
          <button
            type="button"
            onClick={() => setDraft("")}
            className="absolute right-2 inline-flex size-7 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Qidiruvni tozalash"
          >
            <XIcon className="size-4" />
          </button>
        )}
      </label>

      {filters.map((filter) => (
        <Select
          key={filter.key}
          value={values[filter.key] ?? ALL}
          onValueChange={(v) => onFilter(filter.key, v === ALL ? undefined : v)}
        >
          <SelectTrigger className="min-w-[150px]" aria-label={filter.label}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>{filter.label}: barchasi</SelectItem>
            {filter.options.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ))}

      {ordering && (
        <Select value={ordering.value} onValueChange={ordering.onChange}>
          <SelectTrigger className="min-w-[170px]" aria-label="Saralash">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ordering.options.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </div>
  );
}
