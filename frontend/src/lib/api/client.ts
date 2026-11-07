/**
 * Browser API client.
 *
 * - Same-origin only: `/api/v1/*` is proxied to Django by a Next.js route handler,
 *   so the httpOnly auth cookies are first-party and never readable by JS.
 * - Unsafe methods send the Django CSRF token (double-submit cookie).
 * - A 401 triggers exactly one refresh (shared by concurrent requests), then a retry.
 */

export const API_BASE = "/api/v1";

export interface ApiErrorBody {
  code: string;
  message: string;
  details: Record<string, string[] | string> | { retry_after?: number } | null;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: ApiErrorBody["details"] = null,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** Field errors from a 400 response, flattened to one message per field. */
  get fieldErrors(): Record<string, string> {
    if (this.code !== "validation_error" || !this.details) return {};
    const out: Record<string, string> = {};
    for (const [key, value] of Object.entries(this.details)) {
      out[key] = Array.isArray(value) ? String(value[0]) : String(value);
    }
    return out;
  }
}

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.split("; ").find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split("=")[1]) : null;
}

let csrfPromise: Promise<void> | null = null;
async function ensureCsrf(): Promise<string> {
  let token = readCookie("csrftoken");
  if (!token) {
    csrfPromise ??= fetch(`${API_BASE}/auth/csrf/`, { credentials: "same-origin" }).then(() => undefined);
    await csrfPromise;
    csrfPromise = null;
    token = readCookie("csrftoken");
  }
  return token ?? "";
}

let refreshPromise: Promise<boolean> | null = null;
function refreshSession(): Promise<boolean> {
  refreshPromise ??= (async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh/`, {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": await ensureCsrf() },
      });
      return res.ok;
    } catch {
      return false;
    } finally {
      setTimeout(() => (refreshPromise = null), 0);
    }
  })();
  return refreshPromise;
}

/** Called when the session is definitively gone (refresh failed). */
let onSessionExpired: (() => void) | null = null;
export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler;
}

export interface RequestOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined | null>;
  signal?: AbortSignal;
  /** Skip the automatic refresh-and-retry on 401 (auth endpoints). */
  noRefresh?: boolean;
}

function buildUrl(path: string, params?: RequestOptions["params"]) {
  const url = `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
  if (!params) return url;
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") qs.set(key, String(value));
  }
  const query = qs.toString();
  return query ? `${url}?${query}` : url;
}

async function parseError(res: Response): Promise<ApiError> {
  try {
    const data = await res.json();
    const err = data?.error as ApiErrorBody | undefined;
    if (err) return new ApiError(res.status, err.code, err.message, err.details);
  } catch {
    /* non-JSON error */
  }
  return new ApiError(res.status, "server_error", "Server bilan bog'lanishda xatolik yuz berdi.");
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = { Accept: "application/json" };
  let body: BodyInit | undefined;

  if (options.body instanceof FormData) {
    body = options.body;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const send = async () => {
    if (!SAFE_METHODS.has(method)) headers["X-CSRFToken"] = await ensureCsrf();
    return fetch(buildUrl(path, options.params), {
      method,
      headers,
      body,
      credentials: "same-origin",
      signal: options.signal,
      cache: "no-store",
    });
  };

  let res: Response;
  try {
    res = await send();
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    throw new ApiError(0, "network_error", "Tarmoq xatosi. Internet aloqasini tekshiring.");
  }

  if (res.status === 401 && !options.noRefresh) {
    const refreshed = await refreshSession();
    if (refreshed) {
      res = await send();
    } else {
      onSessionExpired?.();
    }
  }

  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, params?: RequestOptions["params"], signal?: AbortSignal) =>
    apiRequest<T>(path, { params, signal }),
  post: <T>(path: string, body?: unknown, opts: Omit<RequestOptions, "body" | "method"> = {}) =>
    apiRequest<T>(path, { ...opts, method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => apiRequest<T>(path, { method: "PATCH", body }),
  delete: (path: string) => apiRequest<void>(path, { method: "DELETE" }),
};

/** Build multipart form data only when a file is involved; otherwise send JSON. */
export function toPayload(values: Record<string, unknown>): FormData | Record<string, unknown> {
  const hasFile = Object.values(values).some((v) => v instanceof File);
  if (!hasFile) return values;
  const form = new FormData();
  for (const [key, value] of Object.entries(values)) {
    if (value === undefined) continue;
    if (Array.isArray(value)) value.forEach((item) => form.append(key, String(item)));
    else if (value instanceof File) form.append(key, value);
    else if (value === null) form.append(key, "");
    else form.append(key, String(value));
  }
  return form;
}
