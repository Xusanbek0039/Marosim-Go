"use client";

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "motion/react";
import { ThemeProvider } from "next-themes";
import { useState } from "react";

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ApiError } from "@/lib/api/client";
import { MotionPreferenceProvider, useMotionPreference } from "@/motion/preference";

function makeQueryClient() {
  return new QueryClient({
    queryCache: new QueryCache(),
    mutationCache: new MutationCache(),
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.status > 0 && error.status < 500) return false;
          return failureCount < 2;
        },
      },
    },
  });
}

function MotionRoot({ children }: { children: React.ReactNode }) {
  const { reduced } = useMotionPreference();
  return <MotionConfig reducedMotion={reduced ? "always" : "user"}>{children}</MotionConfig>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(makeQueryClient);
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>
        <MotionPreferenceProvider>
          <MotionRoot>
            <TooltipProvider delayDuration={250}>
              {children}
              <Toaster position="top-right" richColors closeButton />
            </TooltipProvider>
          </MotionRoot>
        </MotionPreferenceProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
