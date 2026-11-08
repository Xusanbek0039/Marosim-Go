import { CeremonyDetail } from "./ceremony-detail";

/** Static export: one page for every ceremony (the client reads the real id from the URL). */
export function generateStaticParams() {
  return [{ id: "_" }];
}

export default function StudioCeremonyPage() {
  return <CeremonyDetail />;
}
