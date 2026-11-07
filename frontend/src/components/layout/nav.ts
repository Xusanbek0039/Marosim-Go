import {
  ActivityIcon,
  HardDriveIcon,
  LayoutDashboardIcon,
  type LucideIcon,
  Settings2Icon,
  ShieldCheckIcon,
  UsersIcon,
  VideoIcon,
} from "lucide-react";

import type { Me, PermissionCode } from "@/lib/api/types";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Needed permission; `"super"` = SUPER_ADMIN only; undefined = every panel user. */
  requires?: PermissionCode | "super";
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboardIcon, requires: "dashboard.view" },
  { href: "/users", label: "Foydalanuvchilar", icon: UsersIcon, requires: "users.view" },
  { href: "/admins", label: "Adminlar", icon: ShieldCheckIcon, requires: "super" },
  { href: "/studios", label: "Studiyalar", icon: VideoIcon, requires: "studios.view" },
  { href: "/monitoring", label: "API Monitoring", icon: ActivityIcon, requires: "super" },
  { href: "/storage", label: "Google Drive", icon: HardDriveIcon, requires: "super" },
  { href: "/settings", label: "Sozlamalar", icon: Settings2Icon },
];

export function canSee(me: Me | undefined, item: Pick<NavItem, "requires">) {
  if (!me) return false;
  if (!item.requires) return true;
  if (item.requires === "super") return me.role === "SUPER_ADMIN";
  return me.permissions.includes(item.requires);
}

export function firstAllowedPath(me: Me | undefined) {
  return NAV_ITEMS.find((item) => canSee(me, item))?.href ?? "/settings";
}
