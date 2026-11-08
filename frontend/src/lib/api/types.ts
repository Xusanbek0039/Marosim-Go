export type Role = "SUPER_ADMIN" | "ADMIN" | "STUDIO" | "VENUE_OWNER" | "USER";

export type PermissionCode =
  | "dashboard.view"
  | "users.view"
  | "users.create"
  | "users.update"
  | "users.delete"
  | "users.view_pinfl"
  | "studios.view"
  | "studios.create"
  | "studios.update"
  | "studios.delete"
  | "venues.view"
  | "venues.create"
  | "venues.update"
  | "venues.delete"
  | "venues.publish"
  | "subscriptions.view"
  | "subscriptions.create"
  | "subscriptions.update"
  | "subscriptions.plans";

export interface Me {
  id: string;
  /** E.164 login identifier; null only for legacy accounts that were never assigned one. */
  phone_number: string | null;
  is_phone_verified: boolean;
  email: string | null;
  first_name: string;
  last_name: string;
  full_name: string;
  role: Role;
  profile_picture: string | null;
  address: string;
  pinfl_masked: string | null;
  permissions: PermissionCode[];
  last_login: string | null;
  created_at: string;
}

export interface UserSummary {
  id: string;
  phone_number: string | null;
  email: string | null;
  first_name: string;
  last_name: string;
  full_name: string;
  role: Role;
  profile_picture: string | null;
  pinfl_masked: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ManagedUser extends UserSummary {
  is_phone_verified: boolean;
  address: string;
  last_login: string | null;
  updated_at: string;
}

export interface Admin extends ManagedUser {
  permissions: PermissionCode[];
}

export interface Studio {
  id: string;
  name: string;
  profile_picture: string | null;
  address: string;
  responsible_user: UserSummary;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PermissionDef {
  code: PermissionCode;
  module: string;
  module_label: string;
  label: string;
}

export interface Paginated<T> {
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface DashboardOverview {
  totals: {
    users: number;
    active_users: number;
    inactive_users: number;
    new_users_30d: number;
    admins: number;
    studios: number;
    active_studios: number;
  };
  role_distribution: { role: Role; label: string; count: number }[];
  recent_profiles: UserSummary[];
  generated_at: string;
}

export interface ListParams {
  page?: number;
  page_size?: number;
  search?: string;
  ordering?: string;
  is_active?: "true" | "false";
  role?: Role;
  [key: string]: string | number | undefined;
}

// --------------------------------------------------------------- monitoring
export type MonitoringWindow = "15m" | "1h" | "24h" | "7d";
export type EndpointStatus = "healthy" | "degraded" | "failing" | "idle";
export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface MonitoringOverview {
  window: MonitoringWindow;
  bucket: "minute" | "hour";
  from: string;
  to: string;
  totals: {
    total: number;
    success: number;
    client_errors: number;
    server_errors: number;
    throttled: number;
    avg_ms: number | null;
    p95_ms: number | null;
    rpm: number;
    rpm_last_minute: number;
    active_endpoints: number;
    documented_endpoints: number;
    success_rate: number | null;
  };
  series: { t: string; total: number; client_errors: number; server_errors: number; avg_ms: number | null }[];
  top_endpoints: {
    method: HttpMethod;
    route: string;
    count: number;
    client_errors: number;
    server_errors: number;
    avg_ms: number | null;
    max_ms: number | null;
    status: EndpointStatus;
  }[];
  status_codes: { status_code: number; count: number }[];
  error_categories: { error_category: string; count: number }[];
  security: { logins: number; failed_logins: number; lockouts: number; token_reuse: number; registrations: number };
}

export interface RequestLogEntry {
  id: number;
  timestamp: string;
  method: HttpMethod;
  path: string;
  route: string;
  status_code: number;
  duration_ms: number;
  request_id: string;
  user_id: string | null;
  error_category: string;
}

/** Role classification of an operation. PUBLIC = no authentication needed. */
export type ApiRole = "PUBLIC" | Role;

export interface EndpointDoc {
  id: string;
  method: HttpMethod;
  path: string;
  summary: string;
  description: string;
  tags: string[];
  deprecated: boolean;
  auth_required: boolean;
  roles: Role[];
  permission: PermissionCode | null;
  access_label: string;
  /** Role metadata derived on the backend from the real DRF permission classes. */
  allowed_roles: ApiRole[];
  auth_type: "NONE" | "JWT" | "UNKNOWN";
  required_permissions: string[];
  role_requirements: Partial<Record<ApiRole, string[]>>;
  ownership_scope: string | null;
  conditions: string[];
  permission_classes: string[];
  access_status: "DERIVED" | "REVIEW_REQUIRED";
  review_reasons: string[];
  documentation_status: "DOCUMENTED" | "MISSING";
  documentation_missing: string[];
  contract_status: "MATCHES_CONTRACT" | "NOT_IN_CONTRACT" | "CONTRACT_MISMATCH" | "REVIEW_REQUIRED";
  api_version: string;
  parameters: { name: string; in: "path" | "query" | "header" | "cookie"; required: boolean; type: string; description: string }[];
  request_content_type: string | null;
  request_example: unknown;
  success_status: number | null;
  response_example: unknown;
  responses: { status: number; description: string }[];
  status: EndpointStatus;
  traffic_24h: {
    count: number;
    client_errors: number;
    server_errors: number;
    avg_ms: number | null;
    last_seen: string | null;
  };
}

export interface EndpointCatalog {
  api_base_url: string;
  schema_url: string;
  docs_url: string;
  openapi_version: string;
  api_version: string;
  count: number;
  results: EndpointDoc[];
}

export interface ChangelogEntry {
  revision: number;
  date: string;
  note: string;
  added: string[];
  removed: string[];
  changed: Record<string, string[]>;
  breaking: string[];
  schema_changed: string[];
}

export interface DevcenterOverview {
  api_version: string;
  openapi_version: string;
  schema_url: string;
  docs_url: string;
  versions: string[];
  totals: {
    operations: number;
    documented: number;
    documentation_missing: number;
    review_required: number;
    deprecated: number;
    called_24h: number;
  };
  roles: { role: ApiRole; count: number }[];
  methods: Partial<Record<HttpMethod, number>>;
  contract: Partial<Record<EndpointDoc["contract_status"], number>>;
  health: Partial<Record<EndpointStatus, number>>;
  tags: string[];
  last_change: ChangelogEntry | null;
}

export interface MobileFeature {
  key: string;
  label: string;
  status: "AVAILABLE" | "PLANNED" | "INCOMPLETE";
  planned: string;
  missing_operations: string[];
  operations: { id: string; method: HttpMethod; path: string; summary: string; allowed_roles: ApiRole[]; status: EndpointStatus }[];
}

export interface MobileGuide {
  apps: { key: "user" | "studio"; label: string; role: Role; features: MobileFeature[] }[];
}

export interface HealthProbe {
  live: boolean;
  ready: "ok" | "degraded" | "unavailable";
  checks: Record<string, "ok" | "fail">;
  latency_ms: number | null;
  checked_at: string;
}

// ------------------------------------------------------------------ storage
export type StorageStatus = "DISCONNECTED" | "CONNECTED" | "RECONNECT_REQUIRED" | "ERROR";

export interface StorageConnection {
  provider: "GOOGLE_DRIVE";
  status: StorageStatus;
  account_email: string;
  root_folder_id: string;
  root_folder_name: string;
  scopes: string[];
  connected_by: string | null;
  connected_at: string | null;
  last_checked_at: string | null;
  last_success_at: string | null;
  last_error_code: string;
}

export interface GoogleDriveStatus {
  connection: StorageConnection;
  has_credential: boolean;
  configuration: {
    configured: boolean;
    issues: { code: string; message: string }[];
    source: "file" | "env" | null;
    project_id: string;
    client_id_hint: string;
    redirect_uri: string;
    scopes: string[];
  };
  picker: { app_id: string; ready: boolean };
}

export interface GoogleDriveTest {
  ok: boolean;
  account_email: string;
  quota_limit: number | null;
  quota_usage: number | null;
  connection: StorageConnection;
}

// -------------------------------------------------------------------- venues
export type VenueRegion =
  | "TASHKENT_CITY" | "TASHKENT" | "ANDIJAN" | "BUKHARA" | "FERGANA" | "JIZZAKH" | "KHOREZM"
  | "NAMANGAN" | "NAVOI" | "KASHKADARYA" | "KARAKALPAKSTAN" | "SAMARKAND" | "SIRDARYO" | "SURKHANDARYA";
export type VenueType = "BANQUET_HALL" | "RESTAURANT" | "CAFE" | "OUTDOOR" | "OTHER";
export type PublicationStatus = "PRIVATE" | "PENDING_APPROVAL" | "APPROVED" | "REJECTED" | "SUSPENDED";
export type VenueMemberRole = "OWNER" | "MANAGER" | "SCHEDULER" | "VIEWER";

export interface VenueHall {
  id: string;
  name: string;
  capacity: number;
  base_price: string | null;
  effective_base_price: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface VenueImage {
  id: string;
  image: string;
  position: number;
  created_at: string;
}

export interface AdminVenue {
  id: string;
  name: string;
  description: string;
  venue_type: VenueType;
  address: string;
  region: VenueRegion;
  district: string;
  latitude: string | null;
  longitude: string | null;
  phone_number: string;
  cover_image: string | null;
  capacity_min: number;
  capacity_max: number;
  base_price: string;
  currency: "UZS";
  is_active: boolean;
  publication_status: PublicationStatus;
  halls: VenueHall[];
  images: VenueImage[];
  members: {
    membership_id: string;
    user_id: string;
    full_name: string;
    phone_number: string;
    role: VenueMemberRole;
    is_active: boolean;
  }[];
  created_at: string;
  updated_at: string;
}
