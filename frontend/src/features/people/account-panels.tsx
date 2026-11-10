"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckIcon, FolderHeartIcon, FolderOpenIcon, PencilIcon, XIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useCan } from "@/features/auth/hooks";
import { api, ApiError } from "@/lib/api/client";
import { formatDate } from "@/lib/format";

type AccountFeature = { code: string; role: string; label: string; enabled: boolean; platform_enabled: boolean };
type Folder = {
  id: string;
  folder_name: string;
  is_custom: boolean;
  title: string;
  event_date: string;
  status: string;
  studio: { id: string; name: string };
  access_role: "OWNER" | "VIEWER";
};

const message = (e: unknown, fallback: string) => (e instanceof ApiError ? e.message : fallback);

/** "Platforma boshqaruvi" switches, but for this one account (on top of the role-wide ones). */
export function AccountFeatures({ userId }: { userId: string }) {
  const can = useCan();
  const qc = useQueryClient();
  const key = ["account-features", userId];
  const query = useQuery({ queryKey: key, queryFn: () => api.get<AccountFeature[]>(`/users/${userId}/features/`), enabled: can("platform.view") });
  const update = useMutation({
    mutationFn: (disabled_features: string[]) => api.patch<AccountFeature[]>(`/users/${userId}/features/`, { disabled_features }),
    onSuccess: (data) => {
      qc.setQueryData(key, data);
      toast.success("Profil imkoniyatlari yangilandi");
    },
    onError: (e) => toast.error(message(e, "Saqlanmadi")),
  });
  if (!can("platform.view")) return null;
  if (!query.data) return query.isPending ? <p className="text-sm text-muted-foreground">Imkoniyatlar yuklanmoqda…</p> : null;
  if (query.data.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-bold">Imkoniyatlar (shu profil uchun)</p>
      <div className="flex flex-col gap-1.5">
        {query.data.map((f) => (
          <label key={f.code} className="flex items-center justify-between gap-3 rounded-xl bg-muted/40 px-3 py-2.5 text-sm font-medium">
            <span>
              {f.label}
              {!f.platform_enabled && <span className="block text-xs font-normal text-warning">Platforma bo&apos;yicha butun rol uchun o&apos;chirilgan</span>}
            </span>
            <Switch
              aria-label={f.label}
              checked={f.enabled}
              disabled={!can("platform.manage") || update.isPending}
              onCheckedChange={(enabled) =>
                update.mutate(query.data.filter((x) => (x.code === f.code ? !enabled : !x.enabled)).map((x) => x.code))
              }
            />
          </label>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">O&apos;chirilgan imkoniyatdan bu hisob foydalana olmaydi (serverda ham tekshiriladi).</p>
    </div>
  );
}

/** The user's "Mening marosimlarim" folders: own wedding / shared with them; renaming needs users.update. */
export function AccountFolders({ userId }: { userId: string }) {
  const can = useCan();
  const query = useQuery({ queryKey: ["account-folders", userId], queryFn: () => api.get<Folder[]>(`/users/${userId}/folders/`), enabled: can("users.view") });
  if (!can("users.view") || !query.data) return null;
  if (query.data.length === 0) {
    return (
      <div className="flex flex-col gap-1">
        <p className="text-sm font-bold">Marosim papkalari</p>
        <p className="text-sm text-muted-foreground">Bu foydalanuvchida hali marosim yo&apos;q.</p>
      </div>
    );
  }
  const groups: [string, Folder[]][] = [
    ["O'z to'yi", query.data.filter((f) => f.access_role === "OWNER")],
    ["Ruxsat berilganlar", query.data.filter((f) => f.access_role === "VIEWER")],
  ];
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm font-bold">Marosim papkalari</p>
      {groups.map(([label, items]) =>
        items.length ? (
          <div key={label} className="flex flex-col gap-1.5">
            <p className="text-xs font-semibold text-muted-foreground uppercase">{label}</p>
            {items.map((f) => (
              <FolderRow key={f.id} userId={userId} folder={f} canEdit={can("users.update")} />
            ))}
          </div>
        ) : null,
      )}
    </div>
  );
}

function FolderRow({ userId, folder, canEdit }: { userId: string; folder: Folder; canEdit: boolean }) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(folder.folder_name);
  const rename = useMutation({
    mutationFn: (value: string) => api.patch<{ folder_name: string }>(`/users/${userId}/folders/${folder.id}/`, { name: value }),
    onSuccess: (res) => {
      setName(res.folder_name);
      setEditing(false);
      qc.invalidateQueries({ queryKey: ["account-folders", userId] });
      toast.success("Papka nomi saqlandi");
    },
    onError: (e) => toast.error(message(e, "Saqlanmadi")),
  });
  const Icon = folder.access_role === "OWNER" ? FolderHeartIcon : FolderOpenIcon;
  return (
    <div className="flex items-center gap-3 rounded-xl bg-muted/40 px-3 py-2.5 text-sm">
      <Icon className="size-5 shrink-0 text-cyan-600 dark:text-cyan-300" aria-hidden />
      {editing ? (
        <form
          className="flex flex-1 items-center gap-1.5"
          onSubmit={(e) => {
            e.preventDefault();
            rename.mutate(name.trim());
          }}
        >
          <Input autoFocus maxLength={100} value={name} onChange={(e) => setName(e.target.value)} placeholder={folder.title} className="h-9" aria-label="Papka nomi" />
          <button type="submit" disabled={rename.isPending} aria-label="Saqlash" className="rounded-lg p-1.5 text-success hover:bg-muted">
            <CheckIcon className="size-4" />
          </button>
          <button type="button" onClick={() => (setEditing(false), setName(folder.folder_name))} aria-label="Bekor qilish" className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted">
            <XIcon className="size-4" />
          </button>
        </form>
      ) : (
        <>
          <div className="min-w-0 flex-1">
            <p className="truncate font-semibold">{name}</p>
            <p className="truncate text-xs text-muted-foreground">
              {folder.is_custom ? `${folder.title} · ` : ""}
              {formatDate(folder.event_date)} · {folder.studio.name}
            </p>
          </div>
          {canEdit && (
            <button type="button" onClick={() => setEditing(true)} aria-label="Papka nomini o'zgartirish" className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground">
              <PencilIcon className="size-4" />
            </button>
          )}
        </>
      )}
    </div>
  );
}
