import type { Role } from "./types";

export const APP = {
  name: "MarosimGo Studiya",
  tagline: "Studiya kabineti — marosimlar va ishtirokchilar",
  role: "STUDIO" as Role,
  home: "/",
  nav: [
    { href: "/", label: "Marosimlar" },
    { href: "/portfolio", label: "Portfolio" },
    { href: "/galichka", label: "Galichka" },
    { href: "/yordam", label: "Yordam" },
    { href: "/profile", label: "Profil" },
  ],
  allowRegister: false,
  wrongAppMessage: "Bu hisob studiya kabineti uchun emas. O'z ilovangizdan kiring.",
} as const;
