import type { NextRequest } from "next/server";

import { forwardToBackend } from "@/lib/backend-proxy";

const handler = (request: NextRequest) => forwardToBackend(request);

export { handler as DELETE, handler as GET, handler as HEAD, handler as OPTIONS, handler as PATCH, handler as POST, handler as PUT };
