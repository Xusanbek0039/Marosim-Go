"use client";

import { PauseIcon, PlayIcon, RotateCwIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useMemo, useState } from "react";

import { EmptyState, ErrorState, GlassCard, Pagination, RowsSkeleton } from "@/components/common";
import { ListToolbar } from "@/components/common/list-toolbar";
import { CopyButton } from "@/components/monitoring/code-block";
import { MethodBadge, StatusCode } from "@/components/monitoring/primitives";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

import { useRequestLogs } from "./api";

const CATEGORY_LABELS: Record<string, string> = {
  validation: "Validatsiya",
  authentication: "Autentifikatsiya",
  permission: "Ruxsat",
  not_found: "Topilmadi",
  method_not_allowed: "Metod",
  conflict: "Konflikt",
  payload: "Hajm/format",
  throttled: "Throttling",
  client_error: "Mijoz xatosi",
  server_error: "Server xatosi",
};

const FILTERS = [
  {
    key: "method",
    label: "Metod",
    options: ["GET", "POST", "PATCH", "PUT", "DELETE"].map((m) => ({ value: m, label: m })),
  },
  {
    key: "status_class",
    label: "Status",
    options: ["2xx", "3xx", "4xx", "5xx"].map((s) => ({ value: s, label: s })),
  },
  {
    key: "error_category",
    label: "Xato turi",
    options: Object.entries(CATEGORY_LABELS).map(([value, label]) => ({ value, label })),
  },
];

const ORDERING = [
  { value: "-created_at", label: "Eng yangilari" },
  { value: "-duration_ms", label: "Eng sekinlari" },
  { value: "created_at", label: "Eng eskilari" },
];

const pad = (n: number) => String(n).padStart(2, "0");
const time = (iso: string) => {
  const d = new Date(iso);
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};

export function LogsTab() {
  const [page, setPage] = useState(1);
  const [path, setPath] = useState("");
  const [ordering, setOrdering] = useState("-created_at");
  const [filters, setFilters] = useState<Record<string, string | undefined>>({});
  const [live, setLive] = useState(true);

  const params = useMemo(
    () => ({ page, page_size: 25, ordering, path: path || undefined, ...filters }),
    [page, ordering, path, filters],
  );
  const { data, error, isPending, isFetching, refetch } = useRequestLogs(params, live && page === 1);
  const hasQuery = Boolean(path) || Object.values(filters).some(Boolean);

  return (
    <GlassCard className="flex flex-col gap-4 p-4 sm:p-5">
      <div className="flex flex-wrap items-center gap-2.5">
        <div className="min-w-0 flex-1">
          <ListToolbar
            search={path}
            onSearch={(v) => {
              setPath(v);
              setPage(1);
            }}
            placeholder="Yo'l bo'yicha filtr (masalan: auth/login)"
            filters={FILTERS}
            values={filters}
            onFilter={(key, value) => {
              setFilters((prev) => ({ ...prev, [key]: value }));
              setPage(1);
            }}
            ordering={{
              value: ordering,
              options: ORDERING,
              onChange: (v) => {
                setOrdering(v);
                setPage(1);
              },
            }}
          />
        </div>
        <Button variant="outline" onClick={() => setLive((v) => !v)} aria-pressed={live}>
          {live ? <PauseIcon /> : <PlayIcon />}
          {live ? "Jonli" : "To'xtatilgan"}
          {live && (
            <motion.span
              className="size-2 rounded-full bg-emerald-500"
              animate={{ opacity: [1, 0.25, 1] }}
              transition={{ duration: 1.4, repeat: Infinity }}
              aria-hidden
            />
          )}
        </Button>
        <Button variant="outline" size="icon" onClick={() => refetch()} aria-label="Yangilash">
          <RotateCwIcon className={cn(isFetching && "animate-spin")} />
        </Button>
      </div>

      {isPending ? (
        <RowsSkeleton rows={8} />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : data.results.length === 0 ? (
        <EmptyState
          title={hasQuery ? "Mos so'rov topilmadi" : "Hali so'rovlar qayd etilmagan"}
          description={hasQuery ? "Filtrlarni o'zgartirib ko'ring." : "API'ga so'rov kelishi bilan shu yerda paydo bo'ladi."}
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[880px] border-collapse text-sm">
            <thead>
              <tr className="text-left text-xs text-muted-foreground">
                <th className="px-3 py-2.5 font-semibold">Vaqt</th>
                <th className="px-3 py-2.5 font-semibold">So&apos;rov</th>
                <th className="px-3 py-2.5 font-semibold">Status</th>
                <th className="px-3 py-2.5 text-right font-semibold">Davomiyligi</th>
                <th className="px-3 py-2.5 font-semibold">Xato turi</th>
                <th className="px-3 py-2.5 font-semibold">Foydalanuvchi</th>
                <th className="px-3 py-2.5 font-semibold">Request ID</th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence initial={false}>
                {data.results.map((log) => (
                  <motion.tr
                    key={log.id}
                    layout="position"
                    initial={{ opacity: 0, backgroundColor: "rgba(6,182,212,0.14)" }}
                    animate={{ opacity: 1, backgroundColor: "rgba(6,182,212,0)" }}
                    transition={{ duration: 0.8 }}
                    className="border-t border-border/70"
                  >
                    <td className="px-3 py-2.5 whitespace-nowrap text-muted-foreground tabular-nums">
                      <span className="font-semibold text-foreground">{time(log.timestamp)}</span> · {formatDate(log.timestamp)}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="flex min-w-0 items-center gap-2.5">
                        <MethodBadge method={log.method} />
                        <span className="max-w-[320px] truncate font-mono text-xs" title={log.route || log.path}>
                          {log.path}
                        </span>
                      </span>
                    </td>
                    <td className="px-3 py-2.5">
                      <StatusCode code={log.status_code} />
                    </td>
                    <td
                      className={cn(
                        "px-3 py-2.5 text-right whitespace-nowrap tabular-nums",
                        log.duration_ms > 1000 ? "font-semibold text-red-600 dark:text-red-400" : log.duration_ms > 300 ? "text-amber-600 dark:text-amber-300" : "text-muted-foreground",
                      )}
                    >
                      {log.duration_ms.toFixed(1)} ms
                    </td>
                    <td className="px-3 py-2.5 text-xs text-muted-foreground">{CATEGORY_LABELS[log.error_category] ?? "—"}</td>
                    <td className="px-3 py-2.5 font-mono text-[11px] text-muted-foreground">{log.user_id ? `${log.user_id.slice(0, 8)}…` : "—"}</td>
                    <td className="px-3 py-2.5">
                      <span className="flex items-center gap-1.5">
                        <span className="font-mono text-[11px] text-muted-foreground">{log.request_id.slice(0, 8)}…</span>
                        <CopyButton text={log.request_id} label="Request ID nusxalash" className="h-7 px-2" />
                      </span>
                    </td>
                  </motion.tr>
                ))}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      )}

      {data && <Pagination page={data.page} totalPages={data.total_pages} count={data.count} pageSize={data.page_size} onPage={setPage} />}
      <p className="text-xs text-muted-foreground">
        Jurnalda so&apos;rov/javob tanasi, sarlavhalar, cookie, tokenlar va query string saqlanmaydi; URL ichidagi uzun raqamlar
        yashiriladi. Yozuvlar belgilangan muddatdan keyin avtomatik o&apos;chiriladi.
      </p>
    </GlassCard>
  );
}
