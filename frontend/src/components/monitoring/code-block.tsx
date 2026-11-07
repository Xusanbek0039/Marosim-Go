"use client";

import { CheckIcon, CopyIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import type { SnippetLanguage } from "@/features/monitoring/commands";
import { cn } from "@/lib/utils";
import { spring } from "@/motion/tokens";

const KEYWORDS: Record<SnippetLanguage, string[]> = {
  bash: ["curl"],
  javascript: ["const", "await", "async", "return", "null", "true", "false", "new", "if", "else"],
  python: ["import", "from", "print", "None", "True", "False", "def", "return", "if", "else"],
  json: ["true", "false", "null"],
};

const TOKEN_CLASS = {
  comment: "text-slate-400 italic dark:text-slate-500",
  key: "text-sky-700 dark:text-sky-300",
  string: "text-emerald-700 dark:text-emerald-300",
  number: "text-orange-600 dark:text-orange-300",
  keyword: "text-violet-700 font-semibold dark:text-violet-300",
  placeholder: "rounded bg-amber-400/15 text-amber-700 dark:text-amber-300",
  flag: "text-cyan-700 dark:text-cyan-300",
  plain: "",
} as const;
type TokenKind = keyof typeof TOKEN_CLASS;

/** Tiny single-pass highlighter — enough for generated snippets, no runtime dependency. */
function tokenize(code: string, lang: SnippetLanguage): { kind: TokenKind; text: string }[] {
  const comment = lang === "javascript" ? String.raw`\/\/[^\n]*` : lang === "json" ? "(?!)" : String.raw`#[^\n]*`;
  const keywords = KEYWORDS[lang].join("|");
  const re = new RegExp(
    [
      `(?<comment>${comment})`,
      String.raw`(?<key>"(?:\\.|[^"\\\n])*"(?=\s*:))`,
      String.raw`(?<string>"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\])*')`,
      String.raw`(?<placeholder><[A-Za-z_][\w-]*>)`,
      String.raw`(?<flag>(?<=\s)-{1,2}[A-Za-z][\w-]*)`,
      String.raw`(?<number>\b-?\d+(?:\.\d+)?\b)`,
      `(?<keyword>\\b(?:${keywords})\\b)`,
    ].join("|"),
    "g",
  );
  const out: { kind: TokenKind; text: string }[] = [];
  let last = 0;
  for (const match of code.matchAll(re)) {
    const index = match.index ?? 0;
    if (index > last) out.push({ kind: "plain", text: code.slice(last, index) });
    const kind = (Object.entries(match.groups ?? {}).find(([, v]) => v !== undefined)?.[0] ?? "plain") as TokenKind;
    // Placeholders inside strings stay visible: split the string around them.
    if (kind === "string" || kind === "key") {
      for (const part of match[0].split(/(<[A-Za-z_][\w-]*>)/)) {
        if (part) out.push({ kind: /^<[A-Za-z_][\w-]*>$/.test(part) ? "placeholder" : kind, text: part });
      }
    } else {
      out.push({ kind, text: match[0] });
    }
    last = index + match[0].length;
  }
  if (last < code.length) out.push({ kind: "plain", text: code.slice(last) });
  return out;
}

async function copyText(text: string) {
  if (navigator.clipboard?.writeText) return navigator.clipboard.writeText(text);
  // Non-secure contexts (plain http on a LAN host) have no async clipboard.
  const area = document.createElement("textarea");
  area.value = text;
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  document.execCommand("copy");
  area.remove();
}

export function CopyButton({ text, label = "Nusxa olish", className }: { text: string; label?: string; className?: string }) {
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!copied) return;
    const id = setTimeout(() => setCopied(false), 1600);
    return () => clearTimeout(id);
  }, [copied]);

  return (
    <motion.button
      type="button"
      whileTap={{ scale: 0.92 }}
      onClick={async () => {
        try {
          await copyText(text);
          setCopied(true);
        } catch {
          toast.error("Nusxa olib bo'lmadi");
        }
      }}
      aria-label={copied ? "Nusxa olindi" : label}
      className={cn(
        "inline-flex h-8 items-center gap-1.5 rounded-lg border border-glass-border bg-background/70 px-2.5 text-xs font-semibold text-muted-foreground backdrop-blur transition hover:text-foreground",
        copied && "border-emerald-500/40 text-emerald-600 dark:text-emerald-300",
        className,
      )}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={copied ? "ok" : "copy"}
          initial={{ scale: 0.4, opacity: 0, rotate: -30 }}
          animate={{ scale: 1, opacity: 1, rotate: 0, transition: spring.pop }}
          exit={{ scale: 0.4, opacity: 0, transition: { duration: 0.08 } }}
          className="inline-flex"
        >
          {copied ? <CheckIcon className="size-3.5" /> : <CopyIcon className="size-3.5" />}
        </motion.span>
      </AnimatePresence>
      <span aria-live="polite">{copied ? "Nusxa olindi" : "Nusxa"}</span>
    </motion.button>
  );
}

export function CodeBlock({
  code,
  language,
  className,
  maxHeight = 420,
}: {
  code: string;
  language: SnippetLanguage;
  className?: string;
  maxHeight?: number;
}) {
  const tokens = useMemo(() => tokenize(code, language), [code, language]);
  return (
    <div className={cn("group relative overflow-hidden rounded-2xl border border-glass-border bg-slate-50/80 dark:bg-slate-950/60", className)}>
      <div className="flex items-center justify-between border-b border-glass-border px-4 py-2">
        <span className="text-[11px] font-bold tracking-[0.14em] text-muted-foreground uppercase">{language}</span>
        <CopyButton text={code} />
      </div>
      <pre className="overflow-auto p-4 text-[12.5px] leading-relaxed" style={{ maxHeight }}>
        <code className="font-mono">
          {tokens.map((t, i) => (
            <span key={i} className={TOKEN_CLASS[t.kind]}>
              {t.text}
            </span>
          ))}
        </code>
      </pre>
    </div>
  );
}
