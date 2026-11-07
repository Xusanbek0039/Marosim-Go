export type Role = "SUPER_ADMIN" | "ADMIN" | "STUDIO" | "USER";

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
  | "studios.delete";

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
