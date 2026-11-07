import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";

import { Providers } from "@/components/providers";

import "./globals.css";

const jakarta = Plus_Jakarta_Sans({
  variable: "--font-jakarta",
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "MarosimGo Admin", template: "%s · MarosimGo" },
  description: "MarosimGo Super Admin boshqaruv paneli",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uz" className={jakarta.variable} suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
