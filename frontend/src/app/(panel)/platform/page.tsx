"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ErrorState, GlassCard, PageHeader, RowsSkeleton } from "@/components/common";
import { RequirePermission } from "@/components/layout/require-permission";
import { Switch } from "@/components/ui/switch";
import { useCan } from "@/features/auth/hooks";
import { api } from "@/lib/api/client";

type Feature = { code: string; role: string; label: string; enabled: boolean };
const key = ["platform-policy"];
const roles: Record<string, string> = { PUBLIC: "Mehmonlar", USER: "Foydalanuvchilar", STUDIO: "Studiyalar", VENUE_OWNER: "To'yxonalar" };

function Controls() {
  const qc = useQueryClient();
  const can = useCan();
  const query = useQuery({ queryKey: key, queryFn: () => api.get<Feature[]>("/admin/platform-policy/") });
  const update = useMutation({
    mutationFn: (disabled_features: string[]) => api.patch<Feature[]>("/admin/platform-policy/", { disabled_features }),
    onSuccess: (data) => { qc.setQueryData(key, data); toast.success("Imkoniyatlar yangilandi"); },
    onError: (e) => toast.error(e.message),
  });
  if (query.isPending) return <RowsSkeleton rows={8} />;
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  return <div className="grid gap-5 lg:grid-cols-2">{Object.entries(roles).map(([role, label]) => (
    <GlassCard key={role} className="flex flex-col gap-4">
      <h2 className="text-lg font-bold">{label}</h2>
      {query.data.filter((f) => f.role === role).map((feature) => (
        <label key={feature.code} className="flex items-center justify-between gap-4 rounded-xl bg-muted/40 px-4 py-3 text-sm font-medium">
          <span>{feature.label}</span>
          <Switch aria-label={feature.label} checked={feature.enabled} disabled={!can("platform.manage") || update.isPending}
            onCheckedChange={(enabled) => update.mutate(query.data.filter((f) => f.code === feature.code ? !enabled : !f.enabled).map((f) => f.code))} />
        </label>
      ))}
    </GlassCard>
  ))}</div>;
}

export default function PlatformPage() {
  return <RequirePermission requires="platform.view">
    <PageHeader title="Platforma boshqaruvi" crumb="Rollar imkoniyatlari" />
    <p className="mb-5 text-sm text-muted-foreground">O&apos;zgartirishlar darhol kuchga kiradi. Adminlarga boshqaruv ruxsatini faqat Super admin beradi. O&apos;chirilgan imkoniyatlardan foydalanish serverda ham cheklanadi.</p>
    <Controls />
  </RequirePermission>;
}
