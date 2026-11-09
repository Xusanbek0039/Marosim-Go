import {
  ActivityIcon,
  BookOpenIcon,
  Building2Icon,
  CastleIcon,
  CrownIcon,
  GaugeIcon,
  GemIcon,
  GlobeIcon,
  HardDriveIcon,
  HistoryIcon,
  InboxIcon,
  LifeBuoyIcon,
  ListTreeIcon,
  SmartphoneIcon,
  UserIcon,
  UserCogIcon,
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
  /** Active only on this exact path (for section index pages). */
  exact?: boolean;
  /** Live counter shown next to the label (e.g. pending requests). */
  badge?: "requests" | "support";
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboardIcon, requires: "dashboard.view" },
  { href: "/users", label: "Foydalanuvchilar", icon: UsersIcon, requires: "users.view" },
  { href: "/admins", label: "Adminlar", icon: ShieldCheckIcon, requires: "super" },
  { href: "/studios", label: "Studiyalar", icon: VideoIcon, requires: "studios.view" },
  { href: "/venues", label: "To'yxonalar", icon: CastleIcon, requires: "venues.view" },
  { href: "/subscriptions", label: "Obunalar", icon: GemIcon, requires: "subscriptions.view" },
  { href: "/requests", label: "So'rovlar", icon: InboxIcon, requires: "requests.view", badge: "requests" },
  { href: "/storage", label: "Google Drive", icon: HardDriveIcon, requires: "super" },
  { href: "/support", label: "Yordam", icon: LifeBuoyIcon, badge: "support" },
  { href: "/settings", label: "Sozlamalar", icon: Settings2Icon },
];

/** API Developer Center — SUPER_ADMIN only; every list in it comes from the backend OpenAPI schema. */
export const DEV_NAV_ITEMS: NavItem[] = [
  { href: "/developer", label: "API Overview", icon: GaugeIcon, requires: "super", exact: true },
  { href: "/developer/endpoints", label: "All Endpoints", icon: ListTreeIcon, requires: "super" },
  { href: "/developer/user", label: "User APIs", icon: UserIcon, requires: "super" },
  { href: "/developer/studio", label: "Studio APIs", icon: Building2Icon, requires: "super" },
  { href: "/developer/admin", label: "Admin APIs", icon: UserCogIcon, requires: "super" },
  { href: "/developer/super-admin", label: "Super Admin APIs", icon: CrownIcon, requires: "super" },
  { href: "/developer/public", label: "Public APIs", icon: GlobeIcon, requires: "super" },
  { href: "/developer/mobile", label: "Mobile API", icon: SmartphoneIcon, requires: "super" },
  { href: "/monitoring", label: "API Monitoring", icon: ActivityIcon, requires: "super" },
  { href: "/developer/changelog", label: "API Changelog", icon: HistoryIcon, requires: "super" },
];

export const NAV_SECTIONS: { key: string; title: string; icon: LucideIcon; items: NavItem[]; collapsible?: boolean }[] = [
  { key: "main", title: "Boshqaruv", icon: LayoutDashboardIcon, items: NAV_ITEMS },
  { key: "developer", title: "Developer Center", icon: BookOpenIcon, items: DEV_NAV_ITEMS, collapsible: true },
];

export function isActive(pathname: string, item: Pick<NavItem, "href" | "exact">) {
  return pathname === item.href || (!item.exact && pathname.startsWith(`${item.href}/`));
}

export function canSee(me: Me | undefined, item: Pick<NavItem, "requires">) {
  if (!me) return false;
  if (!item.requires) return true;
  if (item.requires === "super") return me.role === "SUPER_ADMIN";
  return me.permissions.includes(item.requires);
}

export function firstAllowedPath(me: Me | undefined) {
  return NAV_ITEMS.find((item) => canSee(me, item))?.href ?? "/settings";
}
