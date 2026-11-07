import type { Role } from "./types";

export const APP = {
  name: "MarosimGo To'yxona",
  tagline: "To'yxona kabineti — zallar, jamoa va bandlik jadvali",
  role: "VENUE_OWNER" as Role,
  home: "/",
  nav: [
    { href: "/", label: "To'yxonalarim" },
    { href: "/profile", label: "Profil" },
  ],
  allowRegister: false,
  wrongAppMessage: "Bu hisob to'yxona kabineti uchun emas. O'z ilovangizdan kiring.",
} as const;
