import Image from "next/image";

import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <Image
      src="/brand/logo-icon.png"
      alt=""
      width={580}
      height={464}
      priority
      className={cn("h-9 w-auto drop-shadow-[0_6px_18px_rgb(6_182_212/0.35)]", className)}
    />
  );
}

/** Full wordmark; swaps to the light-text variant in dark mode (pure CSS, no flash). */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("relative inline-flex", className)} role="img" aria-label="MarosimGo">
      <Image src="/brand/wordmark.png" alt="" width={1076} height={157} priority className="h-full w-auto dark:hidden" />
      <Image
        src="/brand/wordmark-light.png"
        alt=""
        width={1076}
        height={157}
        priority
        className="hidden h-full w-auto dark:block"
      />
    </span>
  );
}
