import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "../frontend/node_modules/typescript/lib/typescript.js";

const files = ["frontend/src/lib/api/client.ts", "frontend-user/src/lib/api.ts", "frontend-studio/src/lib/api.ts", "frontend-toyxona/src/lib/api.ts"];
const originalFetch = globalThis.fetch;
const originalDocument = globalThis.document;
try {
  for (const [index, file] of files.entries()) {
    const source = await readFile(file, "utf8");
    const js = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
    const { api, ApiError } = await import(`data:text/javascript;base64,${Buffer.from(js).toString("base64")}#${index}`);
    globalThis.document = { cookie: "" };
    let csrfCalls = 0;
    globalThis.fetch = async (url) => {
      if (url.endsWith("/auth/csrf/")) {
        csrfCalls++;
        if (csrfCalls === 1) throw new TypeError("Simulated temporary outage");
        globalThis.document.cookie = "csrftoken=recovered-token";
        return Response.json({ detail: "ok" });
      }
      return Response.json({ saved: true });
    };
    await assert.rejects(api.post("/test/", {}, { noRefresh: true }), (error) => error instanceof ApiError && error.code === "network_error");
    assert.deepEqual(await api.post("/test/", {}, { noRefresh: true }), { saved: true });
    assert.equal(csrfCalls, 2, "A failed CSRF request must not poison subsequent attempts");

    globalThis.document.cookie = "";
    csrfCalls = 0;
    globalThis.fetch = async (url, options) => {
      if (url.endsWith("/auth/csrf/")) {
        csrfCalls++;
        await new Promise((resolve) => setTimeout(resolve, 10));
        globalThis.document.cookie = "csrftoken=shared-token";
        return Response.json({ detail: "ok" });
      }
      assert.equal(options.headers["X-CSRFToken"], "shared-token");
      return Response.json({ saved: true });
    };
    await Promise.all([api.post("/one/", {}, { noRefresh: true }), api.post("/two/", {}, { noRefresh: true })]);
    assert.equal(csrfCalls, 1, "Concurrent writes must share the same CSRF request");
    console.log(`${file}: network recovery and concurrent CSRF passed`);
  }
} finally {
  globalThis.fetch = originalFetch;
  if (originalDocument === undefined) delete globalThis.document;
  else globalThis.document = originalDocument;
}
