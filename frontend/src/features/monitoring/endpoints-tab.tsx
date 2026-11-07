"use client";

import { BookOpenIcon, GlobeIcon, LockIcon, SearchIcon, ShieldCheckIcon, XIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useMemo, useState } from "react";

import { EmptyState, ErrorState, GlassCard } from "@/components/common";
import { CodeBlock, CopyButton } from "@/components/monitoring/code-block";
import { AnimatedTabs, EndpointStatusBadge, MethodBadge, StatusCode } from "@/components/monitoring/primitives";
import { Skeleton } from "@/components/ui/skeleton";
import type { EndpointCatalog, EndpointDoc } from "@/lib/api/types";
import { formatDateTime, formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import { fadeUp, spring } from "@/motion/tokens";

import { curl, fetchSnippet, prettyJson, pythonSnippet, requestSpec, type SnippetLanguage } from "./commands";

const METHODS = ["GET", "POST", "PATCH", "PUT", "DELETE"] as const;
type SnippetTab = "curl" | "fetch" | "python" | "body" | "response";

const SNIPPET_TABS: { value: SnippetTab; label: string }[] = [
  { value: "curl", label: "cURL" },
  { value: "fetch", label: "JavaScript" },
  { value: "python", label: "Python" },
  { value: "body", label: "Request JSON" },
  { value: "response", label: "Response" },
];

/** Schema descriptions are Markdown-lite; render **bold** and `code`, nothing else (no HTML). */
function Prose({ text }: { text: string }) {
  return (
    <div className="flex flex-col gap-2 text-sm leading-relaxed text-muted-foreground">
      {text
        .split(/\n{2,}/)
        .filter(Boolean)
        .map((para, i) => (
          <p key={i}>
            {para.split(/(\*\*[^*]+\*\*|`[^`]+`)/).map((part, j) =>
              part.startsWith("**") ? (
                <strong key={j} className="font-semibold text-foreground">
                  {part.slice(2, -2)}
                </strong>
              ) : part.startsWith("`") ? (
                <code key={j} className="rounded bg-muted px-1 py-0.5 font-mono text-[12px] text-foreground">
                  {part.slice(1, -1)}
                </code>
              ) : (
                part
              ),
            )}
          </p>
        ))}
    </div>
  );
}

function EndpointDetail({ endpoint, baseUrl }: { endpoint: EndpointDoc; baseUrl: string }) {
  const [tab, setTab] = useState<SnippetTab>("curl");
  const spec = useMemo(() => requestSpec(endpoint, baseUrl), [endpoint, baseUrl]);
  const snippets: Record<SnippetTab, { code: string; lang: SnippetLanguage }> = {
    curl: { code: curl(spec), lang: "bash" },
    fetch: { code: fetchSnippet(spec), lang: "javascript" },
    python: { code: pythonSnippet(spec), lang: "python" },
    body: { code: prettyJson(spec.body) || "// Bu so'rov tanasiz yuboriladi", lang: spec.body ? "json" : "javascript" },
    response: {
      code: prettyJson(endpoint.response_example) || `// ${endpoint.success_status ?? 204} — javob tanasi yo'q`,
      lang: endpoint.response_example ? "json" : "javascript",
    },
  };
  const current = snippets[tab];
  const errors = endpoint.responses.filter((r) => r.status >= 400);
  const t = endpoint.traffic_24h;

  return (
    <motion.div key={endpoint.id} variants={fadeUp} initial="initial" animate="animate" className="flex min-w-0 flex-col gap-5">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <MethodBadge method={endpoint.method} />
          <code className="min-w-0 font-mono text-sm font-semibold break-all">{endpoint.path}</code>
          <CopyButton text={endpoint.path} label="Yo'lni nusxalash" />
        </div>
        {endpoint.summary && <h3 className="text-lg font-bold">{endpoint.summary}</h3>}
        {endpoint.description && <Prose text={endpoint.description} />}
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div className="rounded-2xl bg-muted/60 p-3">
          <p className="text-xs text-muted-foreground">Autentifikatsiya</p>
          <p className="mt-1 flex items-center gap-1.5 text-sm font-bold">
            {endpoint.auth_required ? <LockIcon className="size-4 text-blue-600 dark:text-blue-300" /> : <GlobeIcon className="size-4 text-emerald-600 dark:text-emerald-300" />}
            {endpoint.auth_required ? "Talab qilinadi" : "Ochiq"}
          </p>
        </div>
        <div className="rounded-2xl bg-muted/60 p-3">
          <p className="text-xs text-muted-foreground">Rol / ruxsat</p>
          <p className="mt-1 flex items-center gap-1.5 text-sm font-bold">
            <ShieldCheckIcon className="size-4 text-violet-600 dark:text-violet-300" />
            {endpoint.roles.length ? endpoint.roles.join(", ") : endpoint.auth_required ? "Istalgan foydalanuvchi" : "—"}
          </p>
          {endpoint.permission && <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">{endpoint.permission}</p>}
        </div>
        <div className="rounded-2xl bg-muted/60 p-3">
          <p className="text-xs text-muted-foreground">Holat (24 soat)</p>
          <p className="mt-1">
            <EndpointStatusBadge status={endpoint.status} />
          </p>
          <p className="mt-0.5 text-[11px] text-muted-foreground tabular-nums">
            {formatNumber(t.count)} so&apos;rov · {formatNumber(t.server_errors)} ta 5xx
          </p>
        </div>
        <div className="rounded-2xl bg-muted/60 p-3">
          <p className="text-xs text-muted-foreground">O&apos;rtacha / oxirgi</p>
          <p className="mt-1 text-sm font-bold tabular-nums">{t.avg_ms === null ? "—" : `${t.avg_ms} ms`}</p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">{t.last_seen ? formatDateTime(t.last_seen) : "chaqirilmagan"}</p>
        </div>
      </div>

      {endpoint.parameters.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-sm font-bold">Parametrlar</p>
          <div className="overflow-x-auto rounded-2xl border border-glass-border">
            <table className="w-full min-w-[420px] text-sm">
              <tbody>
                {endpoint.parameters.map((p) => (
                  <tr key={`${p.in}-${p.name}`} className="border-t border-border/70 first:border-t-0">
                    <td className="px-3 py-2 font-mono text-xs font-semibold">
                      {p.name}
                      {p.required && <span className="text-red-500">*</span>}
                    </td>
                    <td className="px-3 py-2 text-xs text-muted-foreground">{p.in}</td>
                    <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{p.type}</td>
                    <td className="px-3 py-2 text-xs text-muted-foreground">{p.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm font-bold">So&apos;rov namunasi</p>
          <AnimatedTabs tabs={SNIPPET_TABS} value={tab} onChange={setTab} layoutId="snippet-tab" size="sm" />
        </div>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={tab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.16 }}>
            <CodeBlock code={current.code} language={current.lang} />
          </motion.div>
        </AnimatePresence>
        <p className="text-xs text-muted-foreground">
          Faqat hujjat: qiymatlar namunaviy, <code className="font-mono">&lt;ACCESS_TOKEN&gt;</code> o&apos;rniga o&apos;z tokeningizni qo&apos;ying.
          {endpoint.request_content_type === "multipart/form-data" && " Fayl yuborish uchun multipart/form-data ishlating."}
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-sm font-bold">Javob kodlari</p>
        <ul className="flex flex-col gap-1.5">
          {endpoint.responses.map((r) => (
            <li key={r.status} className="flex items-start gap-3 text-sm">
              <StatusCode code={r.status} />
              <span className="pt-0.5 text-muted-foreground">{r.description || (r.status < 400 ? "Muvaffaqiyatli" : "")}</span>
            </li>
          ))}
        </ul>
        {errors.length > 0 && (
          <p className="text-xs text-muted-foreground">
            Barcha xatolar bitta shaklda: <code className="font-mono">{'{"error": {"code", "message", "details"}}'}</code>
          </p>
        )}
      </div>
    </motion.div>
  );
}

export function EndpointsTab({
  data,
  error,
  isPending,
  onRetry,
}: {
  data: EndpointCatalog | undefined;
  error: unknown;
  isPending: boolean;
  onRetry: () => void;
}) {
  const [query, setQuery] = useState("");
  const [methods, setMethods] = useState<Set<string>>(new Set());
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (data?.results ?? []).filter(
      (e) =>
        (methods.size === 0 || methods.has(e.method)) &&
        (!q || e.path.toLowerCase().includes(q) || e.summary.toLowerCase().includes(q) || e.tags.some((t) => t.includes(q))),
    );
  }, [data, query, methods]);

  if (isPending) {
    return (
      <div className="grid gap-5 lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)]" aria-busy="true">
        <div className="glass flex flex-col gap-3 rounded-3xl p-4">
          {Array.from({ length: 9 }).map((_, i) => (
            <Skeleton key={i} className="h-11 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-[520px] rounded-3xl" />
      </div>
    );
  }
  if (error || !data) return <GlassCard><ErrorState error={error} onRetry={onRetry} /></GlassCard>;

  const selected = filtered.find((e) => e.id === selectedId) ?? filtered[0] ?? null;
  const toggleMethod = (m: string) =>
    setMethods((prev) => {
      const next = new Set(prev);
      if (next.has(m)) next.delete(m);
      else next.add(m);
      return next;
    });

  return (
    <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)]">
      <GlassCard className="flex flex-col gap-3 p-4 lg:sticky lg:top-4">
        <label className="relative flex items-center">
          <span className="sr-only">Endpoint qidirish</span>
          <SearchIcon className="pointer-events-none absolute left-3.5 size-4 text-muted-foreground" aria-hidden />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Yo'l, tavsif yoki teg bo'yicha qidirish"
            className="h-11 w-full rounded-xl border border-input bg-white/60 pr-10 pl-10 text-sm outline-none transition placeholder:text-muted-foreground focus-visible:border-brand focus-visible:ring-4 focus-visible:ring-brand/20 dark:bg-slate-950/40 dark:focus-visible:border-cyan-400/70"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="absolute right-2 inline-flex size-7 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted"
              aria-label="Qidiruvni tozalash"
            >
              <XIcon className="size-4" />
            </button>
          )}
        </label>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Metod filtri">
          {METHODS.map((m) => (
            <button
              key={m}
              type="button"
              aria-pressed={methods.has(m)}
              onClick={() => toggleMethod(m)}
              className={cn(
                "rounded-lg border px-2 py-1 font-mono text-[11px] font-bold transition",
                methods.has(m) ? "border-cyan-400/60 bg-cyan-500/12 text-foreground" : "border-glass-border text-muted-foreground hover:text-foreground",
              )}
            >
              {m}
            </button>
          ))}
        </div>
        <p className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {formatNumber(filtered.length)} / {formatNumber(data.count)} endpoint · OpenAPI {data.openapi_version}
          </span>
          <a href={data.docs_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-brand hover:underline dark:text-cyan-300">
            <BookOpenIcon className="size-3.5" /> Swagger
          </a>
        </p>
        <ul className="-mx-1 flex max-h-[62vh] flex-col gap-1 overflow-y-auto px-1" aria-label="Endpointlar">
          {filtered.length === 0 && <EmptyState title="Endpoint topilmadi" description="Qidiruv yoki filtrni o'zgartiring." />}
          {filtered.map((e) => {
            const active = selected?.id === e.id;
            return (
              <li key={e.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(e.id)}
                  aria-current={active ? "true" : undefined}
                  className={cn(
                    "relative flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left outline-none transition-colors focus-visible:ring-4 focus-visible:ring-brand/25",
                    active ? "" : "hover:bg-muted/70",
                  )}
                >
                  {active && (
                    <motion.span
                      layoutId="endpoint-active"
                      className="absolute inset-0 rounded-xl border border-cyan-400/40 bg-cyan-500/[0.08]"
                      transition={spring.sidebar}
                      aria-hidden
                    />
                  )}
                  <MethodBadge method={e.method} className="relative" />
                  <span className="relative flex min-w-0 flex-1 flex-col">
                    <span className="truncate font-mono text-xs font-semibold">{e.path.replace("/api/v1", "")}</span>
                    <span className="truncate text-[11px] text-muted-foreground">{e.summary || e.tags.join(", ")}</span>
                  </span>
                  <span className="relative flex shrink-0 items-center gap-1.5">
                    {e.auth_required ? <LockIcon className="size-3.5 text-muted-foreground" aria-label="Auth" /> : <GlobeIcon className="size-3.5 text-emerald-500" aria-label="Ochiq" />}
                    <span
                      className={cn(
                        "size-2 rounded-full",
                        { healthy: "bg-emerald-500", degraded: "bg-amber-500", failing: "bg-red-500", idle: "bg-slate-300 dark:bg-slate-600" }[e.status],
                      )}
                      aria-hidden
                    />
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </GlassCard>

      <GlassCard className="min-w-0">
        {selected ? <EndpointDetail endpoint={selected} baseUrl={data.api_base_url} /> : <EmptyState title="Endpoint tanlang" />}
      </GlassCard>
    </div>
  );
}
