"use client";

import {
  AlertTriangleIcon,
  CheckCircle2Icon,
  CloudIcon,
  FolderTreeIcon,
  HardDriveIcon,
  Loader2Icon,
  PlugZapIcon,
  RefreshCwIcon,
  ShieldCheckIcon,
  UnplugIcon,
  type LucideIcon,
} from "lucide-react";
import { motion } from "motion/react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { ErrorState, GlassCard, PageHeader } from "@/components/common";
import { RequirePermission } from "@/components/layout/require-permission";
import { ConfirmDialog } from "@/components/motion/confirm-dialog";
import { PageTransition } from "@/components/motion/page-transition";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  reasonMessage,
  useConnectGoogleDrive,
  useDisconnectGoogleDrive,
  useGoogleDriveStatus,
  useTestGoogleDrive,
} from "@/features/storage/api";
import { ApiError } from "@/lib/api/client";
import type { GoogleDriveTest, StorageStatus } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { listContainer, spring, stagger } from "@/motion/tokens";

const STATUS: Record<StorageStatus | "NOT_CONFIGURED", { label: string; tone: string; dot: string; icon: LucideIcon }> = {
  CONNECTED: { label: "Ulangan", tone: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300", dot: "bg-emerald-500", icon: CheckCircle2Icon },
  DISCONNECTED: { label: "Ulanmagan", tone: "border-glass-border bg-muted/60 text-muted-foreground", dot: "bg-slate-400", icon: UnplugIcon },
  RECONNECT_REQUIRED: { label: "Qayta ulash kerak", tone: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300", dot: "bg-amber-500", icon: AlertTriangleIcon },
  ERROR: { label: "Xatolik", tone: "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300", dot: "bg-red-500", icon: AlertTriangleIcon },
  NOT_CONFIGURED: { label: "Sozlanmagan", tone: "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300", dot: "bg-red-500", icon: AlertTriangleIcon },
};

const SCOPE_LABELS: Record<string, string> = {
  openid: "OpenID",
  "https://www.googleapis.com/auth/userinfo.email": "Email",
  "https://www.googleapis.com/auth/drive.file": "drive.file",
};

const formatBytes = (n: number | null) => {
  if (n === null) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let v = n;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(v < 10 && i > 0 ? 1 : 0)} ${units[i]}`;
};

function StatusPill({ status }: { status: keyof typeof STATUS }) {
  const s = STATUS[status];
  return (
    <motion.span
      key={status}
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1, transition: spring.pop }}
      className={cn("inline-flex h-9 items-center gap-2 rounded-2xl border px-3 text-sm font-bold", s.tone)}
      role="status"
    >
      <span className="relative flex size-2.5">
        {status === "CONNECTED" && (
          <motion.span
            className={cn("absolute inset-0 rounded-full", s.dot)}
            animate={{ scale: [1, 2.4], opacity: [0.6, 0] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: "easeOut" }}
          />
        )}
        <span className={cn("relative size-2.5 rounded-full", s.dot)} />
      </span>
      {s.label}
    </motion.span>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border/70 py-3 text-sm last:border-b-0">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className="min-w-0 text-right font-medium break-all">{children}</span>
    </div>
  );
}

/** Shows the toast for `?google=connected|error&reason=` once, then cleans the URL. */
function CallbackNotice() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const handled = useRef(false);
  useEffect(() => {
    const result = params.get("google");
    if (!result || handled.current) return;
    handled.current = true;
    if (result === "connected") toast.success("Google Drive muvaffaqiyatli ulandi");
    else toast.error(reasonMessage(params.get("reason")), { duration: 9000 });
    router.replace(pathname);
  }, [params, router, pathname]);
  return null;
}

function StorageContent() {
  const { data, error, isPending, refetch } = useGoogleDriveStatus();
  const connect = useConnectGoogleDrive();
  const test = useTestGoogleDrive();
  const disconnect = useDisconnectGoogleDrive();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [lastTest, setLastTest] = useState<GoogleDriveTest | null>(null);

  if (isPending) {
    return (
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]" aria-busy="true">
        <Skeleton className="h-96 rounded-3xl" />
        <Skeleton className="h-96 rounded-3xl" />
      </div>
    );
  }
  if (error) return <GlassCard><ErrorState error={error} onRetry={() => refetch()} /></GlassCard>;

  const conn = data.connection;
  const cfg = data.configuration;
  const statusKey: keyof typeof STATUS = cfg.configured ? conn.status : "NOT_CONFIGURED";
  const connected = conn.status === "CONNECTED";
  const needsReconnect = conn.status === "RECONNECT_REQUIRED" || conn.status === "ERROR";

  const onConnect = () =>
    connect.mutate(undefined, {
      onError: (e) => toast.error(e instanceof ApiError ? reasonMessage(e.code) : e.message),
    });
  const onTest = () =>
    test.mutate(undefined, {
      onSuccess: (r) => {
        setLastTest(r);
        toast.success("Ulanish ishlayapti");
      },
      onError: (e) => toast.error(e instanceof ApiError ? reasonMessage(e.code) : "Tekshirib bo'lmadi"),
    });

  return (
    <>
      {needsReconnect && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          role="alert"
          className="flex flex-wrap items-center gap-3 rounded-3xl border border-amber-500/30 bg-amber-500/10 px-5 py-4 text-sm text-amber-800 dark:text-amber-200"
        >
          <AlertTriangleIcon className="size-5 shrink-0" aria-hidden />
          <span className="min-w-0 flex-1">
            <b>Google Drive bilan aloqa uzilgan.</b> {reasonMessage(conn.last_error_code)}
          </span>
          <Button size="sm" onClick={onConnect} disabled={connect.isPending || !cfg.configured}>
            <RefreshCwIcon /> Qayta ulash
          </Button>
        </motion.div>
      )}

      <motion.div
        variants={listContainer(stagger.cards)}
        initial="initial"
        animate="animate"
        className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]"
      >
        <GlassCard className="flex flex-col gap-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="flex size-12 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 text-white shadow-lg">
                <HardDriveIcon className="size-6" aria-hidden />
              </span>
              <div>
                <h2 className="text-lg font-bold">Google Drive</h2>
                <p className="text-xs text-muted-foreground">Shaxsiy Gmail · My Drive · OAuth 2.0</p>
              </div>
            </div>
            <StatusPill status={statusKey} />
          </div>

          <div className="rounded-2xl border border-glass-border bg-muted/40 px-4">
            <Row label="Ulangan akkaunt">{conn.account_email || "—"}</Row>
            <Row label="Root papka">
              {conn.root_folder_id ? (
                <span className="font-mono text-xs">{conn.root_folder_name || conn.root_folder_id}</span>
              ) : (
                <span className="text-muted-foreground">Hali tanlanmagan (keyingi bosqich: Google Picker)</span>
              )}
            </Row>
            <Row label="Ruxsatlar (scopes)">
              <span className="inline-flex flex-wrap justify-end gap-1.5">
                {conn.scopes.length === 0
                  ? "—"
                  : conn.scopes.map((s) => (
                      <span key={s} className="rounded-full bg-blue-500/12 px-2 py-0.5 text-[11px] font-semibold text-blue-700 dark:text-blue-300">
                        {SCOPE_LABELS[s] ?? s}
                      </span>
                    ))}
              </span>
            </Row>
            <Row label="Ulagan">{conn.connected_by ?? "—"}</Row>
            <Row label="Ulangan vaqt">{formatDateTime(conn.connected_at)}</Row>
            <Row label="Oxirgi tekshiruv">{formatDateTime(conn.last_checked_at)}</Row>
            <Row label="Oxirgi muvaffaqiyat">{formatDateTime(conn.last_success_at)}</Row>
            {conn.last_error_code && (
              <Row label="Oxirgi xato">
                <span className="font-mono text-xs text-red-600 dark:text-red-400">{conn.last_error_code}</span>
              </Row>
            )}
          </div>

          {lastTest && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col gap-2 rounded-2xl bg-emerald-500/10 p-4 text-sm"
            >
              <p className="flex items-center gap-2 font-semibold text-emerald-700 dark:text-emerald-300">
                <CheckCircle2Icon className="size-4" /> Drive javob berdi: {lastTest.account_email}
              </p>
              {lastTest.quota_limit !== null && (
                <>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <motion.div
                      className="h-full rounded-full bg-gradient-to-r from-blue-600 to-cyan-400"
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.max(2, ((lastTest.quota_usage ?? 0) / lastTest.quota_limit) * 100)}%` }}
                      transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {formatBytes(lastTest.quota_usage)} / {formatBytes(lastTest.quota_limit)} ishlatilgan
                  </p>
                </>
              )}
            </motion.div>
          )}

          <div className="flex flex-wrap gap-2.5">
            {!connected && (
              <Button onClick={onConnect} disabled={connect.isPending || !cfg.configured} size="lg">
                {connect.isPending ? <Loader2Icon className="animate-spin" /> : <PlugZapIcon />}
                {needsReconnect ? "Qayta ulash" : "Connect Google Drive"}
              </Button>
            )}
            {(connected || data.has_credential) && (
              <Button variant="outline" size="lg" onClick={onTest} disabled={test.isPending}>
                {test.isPending ? <Loader2Icon className="animate-spin" /> : <RefreshCwIcon />}
                Test Connection
              </Button>
            )}
            <Button variant="outline" size="lg" disabled title="Keyingi bosqichda (Google Picker)">
              <FolderTreeIcon /> Select Root Folder
            </Button>
            {(connected || data.has_credential) && (
              <Button variant="destructive" size="lg" onClick={() => setConfirmOpen(true)}>
                <UnplugIcon /> Disconnect
              </Button>
            )}
          </div>
        </GlassCard>

        <div className="flex flex-col gap-5">
          <GlassCard className="flex flex-col gap-3">
            <h2 className="flex items-center gap-2 text-lg font-bold">
              <ShieldCheckIcon className="size-5 text-cyan-600 dark:text-cyan-300" aria-hidden /> Server sozlamasi
            </h2>
            {cfg.issues.length > 0 ? (
              <ul className="flex flex-col gap-2">
                {cfg.issues.map((i) => (
                  <li key={i.code} className="rounded-2xl bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-300">
                    <span className="font-mono text-xs font-bold">{i.code}</span>
                    <p>{i.message}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="flex items-center gap-2 text-sm font-semibold text-emerald-700 dark:text-emerald-300">
                <CheckCircle2Icon className="size-4" /> OAuth client va shifrlash kaliti tayyor
              </p>
            )}
            <div className="rounded-2xl border border-glass-border bg-muted/40 px-4">
              <Row label="Manba">{cfg.source === "file" ? "credentials JSON" : cfg.source === "env" ? "environment" : "—"}</Row>
              <Row label="Loyiha">{cfg.project_id || "—"}</Row>
              <Row label="Client ID">
                <span className="font-mono text-[11px]">{cfg.client_id_hint || "—"}</span>
              </Row>
              <Row label="Redirect URI">
                <span className="font-mono text-[11px]">{cfg.redirect_uri}</span>
              </Row>
            </div>
          </GlassCard>

          <GlassCard className="flex flex-col gap-2 text-sm text-muted-foreground">
            <h2 className="flex items-center gap-2 text-lg font-bold text-foreground">
              <CloudIcon className="size-5 text-blue-600 dark:text-blue-300" aria-hidden /> Xavfsizlik
            </h2>
            <p>Refresh token faqat serverda, shifrlangan holda saqlanadi va bu sahifaga hech qachon yuborilmaydi.</p>
            <p>
              <b className="text-foreground">drive.file</b> ruxsati: ilova faqat o&apos;zi yaratgan yoki siz tanlagan fayl/papkalarni
              ko&apos;radi — Drive&apos;ingizdagi boshqa fayllarga kira olmaydi.
            </p>
            <p>OAuth ilova &quot;Testing&quot; holatida bo&apos;lsa, Google refresh tokenni 7 kunda bekor qiladi — keyin qayta ulash kerak.</p>
          </GlassCard>
        </div>
      </motion.div>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        pending={disconnect.isPending}
        tone="danger"
        title="Google Drive'ni uzasizmi?"
        confirmLabel="Uzish"
        description={
          <>
            Token Google&apos;da bekor qilinadi va serverdan o&apos;chiriladi. Drive&apos;dagi fayllar o&apos;chmaydi; keyin qayta
            ulash mumkin.
          </>
        }
        onConfirm={() =>
          disconnect.mutate(undefined, {
            onSuccess: () => {
              toast.success("Google Drive uzildi");
              setConfirmOpen(false);
              setLastTest(null);
            },
            onError: () => toast.error("Uzib bo'lmadi"),
          })
        }
      />
    </>
  );
}

export default function StoragePage() {
  return (
    <RequirePermission requires="super">
      <PageTransition>
        <PageHeader title="Google Drive Storage" crumb="Super Admin / Storage" />
        <Suspense fallback={null}>
          <CallbackNotice />
        </Suspense>
        <StorageContent />
      </PageTransition>
    </RequirePermission>
  );
}
