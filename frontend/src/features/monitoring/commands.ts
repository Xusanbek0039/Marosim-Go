/**
 * Request snippets for the API catalog — documentation only, nothing here sends a request.
 *
 * Each generator turns an `EndpointDoc` into copy-paste code. Secrets are always placeholders
 * (`<ACCESS_TOKEN>`), path parameters become `<name>`. A future in-browser test console can
 * reuse `requestSpec()` and call the API with the admin's own session — never through a
 * server-side proxy that accepts arbitrary URLs.
 */
import type { EndpointDoc } from "@/lib/api/types";

export type SnippetLanguage = "bash" | "javascript" | "python" | "json";

export interface RequestSpec {
  method: string;
  url: string;
  headers: Record<string, string>;
  body: unknown;
}

const hasBody = (method: string) => ["POST", "PUT", "PATCH"].includes(method);

export function requestSpec(endpoint: EndpointDoc, baseUrl: string): RequestSpec {
  const path = endpoint.path.replace(/\{(\w+)\}/g, "<$1>");
  const headers: Record<string, string> = {};
  const body = hasBody(endpoint.method) ? (endpoint.request_example ?? {}) : undefined;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  // Auth endpoints return tokens in the body only for mobile-style clients.
  if (endpoint.path.startsWith("/api/v1/auth/")) headers["X-Client"] = "mobile";
  if (endpoint.auth_required) headers.Authorization = "Bearer <ACCESS_TOKEN>";
  return { method: endpoint.method, url: `${baseUrl.replace(/\/$/, "")}${path}`, headers, body };
}

const json = (value: unknown, indent = 2) => JSON.stringify(value, null, indent);

export function curl(spec: RequestSpec): string {
  const lines = [`curl -X ${spec.method} "${spec.url}"`];
  for (const [key, value] of Object.entries(spec.headers)) lines.push(`  -H "${key}: ${value}"`);
  if (spec.body !== undefined) lines.push(`  -d '${json(spec.body).replace(/'/g, "'\\''")}'`);
  return lines.join(" \\\n");
}

export function fetchSnippet(spec: RequestSpec): string {
  const options = [`  method: "${spec.method}",`];
  if (Object.keys(spec.headers).length) {
    options.push(`  headers: ${json(spec.headers).replace(/\n/g, "\n  ")},`);
  }
  if (spec.body !== undefined) options.push(`  body: JSON.stringify(${json(spec.body).replace(/\n/g, "\n  ")}),`);
  return [
    `const response = await fetch("${spec.url}", {`,
    ...options,
    "});",
    "const data = response.status === 204 ? null : await response.json();",
    "console.log(response.status, data);",
  ].join("\n");
}

function toPython(value: unknown, depth = 0): string {
  const pad = "    ".repeat(depth + 1);
  const end = "    ".repeat(depth);
  if (value === null || value === undefined) return "None";
  if (value === true) return "True";
  if (value === false) return "False";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) {
    if (!value.length) return "[]";
    return `[\n${value.map((v) => `${pad}${toPython(v, depth + 1)},`).join("\n")}\n${end}]`;
  }
  const entries = Object.entries(value as Record<string, unknown>);
  if (!entries.length) return "{}";
  return `{\n${entries.map(([k, v]) => `${pad}${JSON.stringify(k)}: ${toPython(v, depth + 1)},`).join("\n")}\n${end}}`;
}

export function pythonSnippet(spec: RequestSpec): string {
  const args = [`    "${spec.url}",`];
  if (Object.keys(spec.headers).length) args.push(`    headers=${toPython(spec.headers, 1)},`);
  if (spec.body !== undefined) args.push(`    json=${toPython(spec.body, 1)},`);
  args.push("    timeout=10,");
  return [
    "import requests",
    "",
    `response = requests.${spec.method.toLowerCase()}(`,
    ...args,
    ")",
    "print(response.status_code, response.json() if response.content else None)",
  ].join("\n");
}

export const prettyJson = (value: unknown) => (value === undefined || value === null ? "" : json(value));
