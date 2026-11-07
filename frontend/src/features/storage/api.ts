"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { GoogleDriveStatus, GoogleDriveTest, StorageConnection } from "@/lib/api/types";

const BASE = "/admin/storage/google";
export const storageKey = ["storage", "google"] as const;

export function useGoogleDriveStatus() {
  return useQuery({
    queryKey: storageKey,
    queryFn: ({ signal }) => api.get<GoogleDriveStatus>(`${BASE}/status/`, undefined, signal),
    refetchOnWindowFocus: true,
  });
}

/** Only ever navigates to Google's own consent host — never to a URL we did not expect. */
function assertGoogleUrl(raw: string) {
  const url = new URL(raw);
  if (url.protocol !== "https:" || url.hostname !== "accounts.google.com") {
    throw new Error("Kutilmagan yo'naltirish manzili.");
  }
  return url.toString();
}

export function useConnectGoogleDrive() {
  return useMutation({
    mutationFn: async () => {
      const { authorization_url } = await api.get<{ authorization_url: string }>(`${BASE}/connect/`);
      window.location.assign(assertGoogleUrl(authorization_url));
    },
  });
}

export function useTestGoogleDrive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<GoogleDriveTest>(`${BASE}/test/`),
    onSettled: () => qc.invalidateQueries({ queryKey: storageKey }),
  });
}

export function useDisconnectGoogleDrive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<StorageConnection>(`${BASE}/disconnect/`),
    onSettled: () => qc.invalidateQueries({ queryKey: storageKey }),
  });
}

/** Callback `?reason=` codes and backend error codes → what the Super Admin should do. */
export const REASON_MESSAGES: Record<string, string> = {
  access_denied: "Google'da ruxsat berish bekor qilindi.",
  scope_denied: "Google Drive ruxsati belgilanmadi. Qayta ulab, Drive katagini belgilang.",
  no_refresh_token: "Google refresh token bermadi. myaccount.google.com/permissions dan MarosimGo'ni olib tashlab, qayta ulang.",
  state_invalid: "Ulanish so'rovi topilmadi. Paneldan qaytadan boshlang.",
  state_expired: "Ulanish muddati tugadi (10 daqiqa). Qaytadan urinib ko'ring.",
  state_reused: "Bu ulanish havolasi allaqachon ishlatilgan.",
  state_missing: "Ulanish so'rovi noto'g'ri.",
  binding_mismatch: "Ulanish boshqa brauzerdan yakunlandi. Xuddi shu brauzerda qaytadan boshlang.",
  forbidden: "Ulanishni faqat faol Super Admin yakunlay oladi.",
  exchange_failed: "Google kodini tokenga almashtirib bo'lmadi. Client ID/Secret va redirect URI'ni tekshiring.",
  id_token_invalid: "Google akkaunt ma'lumoti tasdiqlanmadi.",
  reconnect_required: "Google ruxsati bekor qilingan yoki muddati tugagan. Qayta ulang.",
  invalid_grant: "Refresh token bekor qilingan yoki muddati tugagan (Testing rejimida 7 kun).",
  not_connected: "Google Drive hali ulanmagan.",
  insufficient_permissions: "Drive ruxsati yetarli emas.",
  storage_quota_exceeded: "Google Drive xotirasi to'lgan.",
  rate_limited: "Google so'rovlar limitiga yetildi. Birozdan so'ng urinib ko'ring.",
  drive_api_disabled: "Google Cloud loyihasida Drive API yoqilmagan.",
  network_error: "Google bilan tarmoq aloqasi yo'q.",
  account_mismatch: "Drive boshqa Google akkauntiga tegishli bo'lib chiqdi. Qayta ulang.",
  encryption_key_missing: "Serverda GOOGLE_TOKEN_ENCRYPTION_KEY sozlanmagan.",
  encryption_key_invalid: "Saqlangan tokenni ochib bo'lmadi (shifrlash kaliti o'zgargan). Qayta ulang.",
  credential_missing: "Saqlangan token topilmadi. Qayta ulang.",
  client_file_missing: "OAuth client JSON fayli serverda topilmadi.",
  redirect_uri_mismatch: "Redirect URI Google Cloud sozlamasiga mos emas.",
};

export const reasonMessage = (code?: string | null) =>
  (code && REASON_MESSAGES[code]) || (code ? `Xatolik: ${code}` : "Noma'lum xatolik");
