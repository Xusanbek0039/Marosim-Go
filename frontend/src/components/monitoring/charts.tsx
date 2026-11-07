"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useId, useMemo, useRef, useState } from "react";

import type { MonitoringOverview } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
import { ease } from "@/motion/tokens";

type Series = MonitoringOverview["series"];
type Point = [number, number];

const HEIGHT = 230;
const PAD = { top: 12, right: 12, bottom: 26, left: 44 };

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.round(entry.contentRect.width)));
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return [ref, width] as const;
}

/** Monotone cubic interpolation (Fritsch–Carlson): smooth, never overshoots the data. */
function monotonePath(points: Point[]): string {
  if (points.length === 0) return "";
  if (points.length === 1) return `M${points[0][0]},${points[0][1]}`;
  const n = points.length;
  const dx: number[] = [];
  const slope: number[] = [];
  for (let i = 0; i < n - 1; i++) {
    dx[i] = points[i + 1][0] - points[i][0];
    slope[i] = (points[i + 1][1] - points[i][1]) / (dx[i] || 1);
  }
  const tangent: number[] = [slope[0]];
  for (let i = 1; i < n - 1; i++) {
    tangent[i] = slope[i - 1] * slope[i] <= 0 ? 0 : (3 * (dx[i - 1] + dx[i])) / ((2 * dx[i] + dx[i - 1]) / slope[i - 1] + (dx[i] + 2 * dx[i - 1]) / slope[i]);
  }
  tangent[n - 1] = slope[n - 2];
  let d = `M${points[0][0]},${points[0][1]}`;
  for (let i = 0; i < n - 1; i++) {
    const [x0, y0] = points[i];
    const [x1, y1] = points[i + 1];
    const h = dx[i] / 3;
    d += `C${x0 + h},${y0 + tangent[i] * h} ${x1 - h},${y1 - tangent[i + 1] * h} ${x1},${y1}`;
  }
  return d;
}

function niceMax(value: number) {
  if (value <= 0) return 4;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 2.5, 5, 10].find((s) => s * magnitude >= value / 4) ?? 10;
  return Math.ceil(value / (step * magnitude)) * step * magnitude;
}

const tickText = (t: number) => (Number.isInteger(t) ? formatNumber(t) : t.toFixed(1));
const pad2 = (n: number) => String(n).padStart(2, "0");
function tickLabel(iso: string, bucket: MonitoringOverview["bucket"], spanDays: boolean) {
  const d = new Date(iso);
  const time = `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
  if (bucket === "hour" && spanDays) return `${pad2(d.getDate())}.${pad2(d.getMonth() + 1)} ${pad2(d.getHours())}:00`;
  return time;
}

interface Layer {
  key: string;
  label: string;
  color: string;
  values: (number | null)[];
  area?: boolean;
}

function ChartFrame({
  series,
  bucket,
  layers,
  unit,
  emptyLabel,
}: {
  series: Series;
  bucket: MonitoringOverview["bucket"];
  layers: Layer[];
  unit?: string;
  emptyLabel: string;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const gradientId = useId();
  const n = series.length;
  const innerW = Math.max(0, width - PAD.left - PAD.right);
  const innerH = HEIGHT - PAD.top - PAD.bottom;
  const max = niceMax(Math.max(0, ...layers.flatMap((l) => l.values.map((v) => v ?? 0))));
  const x = (i: number) => PAD.left + (n <= 1 ? innerW / 2 : (i * innerW) / (n - 1));
  const y = (v: number) => PAD.top + innerH - (v / max) * innerH;
  const base = PAD.top + innerH;
  const hasData = layers.some((l) => l.values.some((v) => (v ?? 0) > 0));
  const spanDays = n > 0 && new Date(series[n - 1].t).getDate() !== new Date(series[0].t).getDate();

  const paths = useMemo(
    () =>
      layers.map((layer) => {
        // Gaps (null) split the line into segments.
        const segments: Point[][] = [];
        let current: Point[] = [];
        layer.values.forEach((v, i) => {
          if (v === null) {
            if (current.length) segments.push(current);
            current = [];
          } else current.push([x(i), y(v)]);
        });
        if (current.length) segments.push(current);
        const line = segments.map(monotonePath).join("");
        const area = layer.area
          ? segments.map((s) => `${monotonePath(s)}L${s[s.length - 1][0]},${base}L${s[0][0]},${base}Z`).join("")
          : "";
        // A lone data point has no line to draw: show it as a dot instead.
        const dots = segments.filter((seg) => seg.length === 1).map((seg) => seg[0]);
        return { ...layer, line, areaPath: area, dots };
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [layers, width, max, n],
  );

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * max);
  const labelEvery = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(innerW / 90))));

  const onMove = (event: React.PointerEvent<SVGRectElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const rel = event.clientX - rect.left;
    const index = n <= 1 ? 0 : Math.round((rel / rect.width) * (n - 1));
    setHover(Math.min(n - 1, Math.max(0, index)));
  };

  return (
    <div ref={ref} className="relative w-full select-none" style={{ height: HEIGHT }}>
      {width > 0 && (
        <svg width={width} height={HEIGHT} role="img" aria-label={layers.map((l) => l.label).join(", ")} className="overflow-visible">
          <defs>
            {layers.map((l) => (
              <linearGradient key={l.key} id={`${gradientId}-${l.key}`} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={l.color} stopOpacity={0.32} />
                <stop offset="100%" stopColor={l.color} stopOpacity={0.02} />
              </linearGradient>
            ))}
            <clipPath id={`${gradientId}-reveal`}>
              <motion.rect
                x={0}
                y={0}
                height={HEIGHT}
                initial={{ width: 0 }}
                animate={{ width }}
                transition={{ duration: 0.9, ease: ease.emphasized }}
              />
            </clipPath>
          </defs>

          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={width - PAD.right} y1={y(t)} y2={y(t)} className="stroke-border" strokeDasharray="3 5" />
              <text x={PAD.left - 8} y={y(t)} dy="0.32em" textAnchor="end" className="fill-muted-foreground text-[10px] tabular-nums">
                {tickText(t)}
                {unit && t > 0 ? unit : ""}
              </text>
            </g>
          ))}
          {series.map((point, i) =>
            i % labelEvery === 0 ? (
              <text key={point.t} x={x(i)} y={HEIGHT - 6} textAnchor="middle" className="fill-muted-foreground text-[10px] tabular-nums">
                {tickLabel(point.t, bucket, spanDays)}
              </text>
            ) : null,
          )}

          <g clipPath={`url(#${gradientId}-reveal)`}>
            {paths.map((p) => (
              <g key={p.key}>
                {p.areaPath && (
                  <motion.path
                    d={p.areaPath}
                    animate={{ d: p.areaPath }}
                    transition={{ duration: 0.6, ease: ease.emphasized }}
                    fill={`url(#${gradientId}-${p.key})`}
                  />
                )}
                <motion.path
                  d={p.line}
                  animate={{ d: p.line }}
                  transition={{ duration: 0.6, ease: ease.emphasized }}
                  fill="none"
                  stroke={p.color}
                  strokeWidth={2.25}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {p.dots.map(([cx, cy]) => (
                  <motion.circle
                    key={`${cx}-${cy}`}
                    cx={cx}
                    cy={cy}
                    r={3.5}
                    fill={p.color}
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 420, damping: 24 }}
                  />
                ))}
              </g>
            ))}
          </g>

          {hover !== null && hasData && (
            <g pointerEvents="none">
              <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={base} className="stroke-muted-foreground/40" />
              {layers.map((l) =>
                l.values[hover] === null ? null : (
                  <circle key={l.key} cx={x(hover)} cy={y(l.values[hover] ?? 0)} r={4} fill={l.color} className="stroke-background" strokeWidth={2} />
                ),
              )}
            </g>
          )}
          <rect
            x={PAD.left}
            y={PAD.top}
            width={innerW}
            height={innerH}
            fill="transparent"
            onPointerMove={onMove}
            onPointerLeave={() => setHover(null)}
          />
        </svg>
      )}

      {!hasData && width > 0 && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
          {emptyLabel}
        </div>
      )}

      <AnimatePresence>
        {hover !== null && hasData && series[hover] && (
          <motion.div
            key="tooltip"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.12 }}
            className="glass-strong pointer-events-none absolute top-2 z-10 min-w-40 rounded-xl px-3 py-2 text-xs"
            style={{ left: Math.min(Math.max(x(hover) - 80, 0), Math.max(0, width - 170)) }}
          >
            <p className="mb-1 font-bold tabular-nums">{tickLabel(series[hover].t, bucket, true)}</p>
            {layers.map((l) => (
              <p key={l.key} className="flex items-center justify-between gap-4">
                <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                  <span className="size-2 rounded-full" style={{ background: l.color }} />
                  {l.label}
                </span>
                <span className="font-semibold tabular-nums">
                  {l.values[hover] === null ? "—" : `${formatNumber(l.values[hover] ?? 0)}${unit ?? ""}`}
                </span>
              </p>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function TrafficChart({ series, bucket }: { series: Series; bucket: MonitoringOverview["bucket"] }) {
  const layers = useMemo<Layer[]>(
    () => [
      { key: "total", label: "Jami", color: "#2563eb", values: series.map((p) => p.total), area: true },
      { key: "client", label: "4xx", color: "#f59e0b", values: series.map((p) => p.client_errors), area: true },
      { key: "server", label: "5xx", color: "#ef4444", values: series.map((p) => p.server_errors), area: true },
    ],
    [series],
  );
  return <ChartFrame series={series} bucket={bucket} layers={layers} emptyLabel="Bu oraliqda so'rovlar qayd etilmagan" />;
}

export function LatencyChart({ series, bucket }: { series: Series; bucket: MonitoringOverview["bucket"] }) {
  const layers = useMemo<Layer[]>(
    () => [{ key: "avg", label: "O'rtacha", color: "#06b6d4", values: series.map((p) => p.avg_ms), area: true }],
    [series],
  );
  return <ChartFrame series={series} bucket={bucket} layers={layers} unit=" ms" emptyLabel="Kechikish ma'lumoti yo'q" />;
}

export function ChartLegend({ items }: { items: { label: string; color: string }[] }) {
  return (
    <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
      {items.map((i) => (
        <span key={i.label} className="inline-flex items-center gap-1.5">
          <span className="size-2.5 rounded-full" style={{ background: i.color }} />
          {i.label}
        </span>
      ))}
    </div>
  );
}
