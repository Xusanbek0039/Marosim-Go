import { AppShell } from "@/components/layout/app-shell";

export default function PanelLayout({ children }: LayoutProps<"/">) {
  return <AppShell>{children}</AppShell>;
}
