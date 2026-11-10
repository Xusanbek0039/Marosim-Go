import type { Role } from "./types";

export const APP = {
  name: "MarosimGo",
  tagline: "Marosimlaringiz, video va suratlaringiz bir joyda",
  role: "USER" as Role,
  home: "/",
  nav: [
    { href: "/", label: "Mening marosimlarim" },
    { href: "/toyxonalar", label: "To'yxonalar" },
    { href: "/studiyalar", label: "Studiyalar" },
    { href: "/xabarlar", label: "Xabarlar" },
    { href: "/bronlarim", label: "Bronlarim" },
    { href: "/obuna", label: "Obuna" },
    { href: "/yordam", label: "Yordam" },
    { href: "/profile", label: "Profil" },
  ],
  allowRegister: true,
  wrongAppMessage: "Bu hisob mijoz ilovasi uchun emas. O'z kabinetingizdan kiring.",
} as const;
