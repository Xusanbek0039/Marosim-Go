import type { Role } from "./types";

export const APP = {
  name: "MarosimGo",
  tagline: "Marosimlaringiz, video va suratlaringiz bir joyda",
  role: "USER" as Role,
  home: "/",
  nav: [
    { href: "/", label: "Marosimlarim" },
    { href: "/toyxonalar", label: "To'yxonalar" },
    { href: "/bronlarim", label: "Bronlarim" },
    { href: "/obuna", label: "Obuna" },
    { href: "/profile", label: "Profil" },
  ],
  allowRegister: true,
  wrongAppMessage: "Bu hisob mijoz ilovasi uchun emas. O'z kabinetingizdan kiring.",
} as const;
