import { VenueDetail } from "./venue-detail";

/** Static export: one page for every id (the client reads the real id from the URL). */
export function generateStaticParams() {
  return [{ id: "_" }];
}

export default function Page() {
  return (
    <VenueDetail />
  );
}
