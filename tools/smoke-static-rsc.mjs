// Verify the browser's flattened RSC prefetch URLs against the real exported segment files.
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { get } from "node:http";

const panels = { panel: "sa.localhost", "panel-admin": "ad.localhost", "panel-user": "us.localhost", "panel-studio": "st.localhost", "panel-toyxona": "ve.localhost" };
let count = 0;
for (const [panel, host] of Object.entries(panels)) {
  const root = resolve("backend", panel);
  function* files(dir) {
    for (const item of readdirSync(dir, { withFileTypes: true })) {
      const file = join(dir, item.name);
      if (item.isDirectory() && item.name !== "_next") yield* files(file);
      else if (item.isFile() && item.name === "__PAGE__.txt") yield file;
    }
  }
  for (const file of files(root)) {
    const parts = relative(root, file).split(/[\\/]/);
    const boundary = parts.findIndex((part) => part.startsWith("__next."));
    assert.ok(boundary >= 0, file);
    const prefix = parts.slice(0, boundary).map((part) => part === "_" ? "00000000-0000-4000-8000-000000000001" : part);
    const url = "/" + [...prefix, parts.slice(boundary).join(".")].join("/");
    const response = await new Promise((done, fail) => {
      get({ hostname: "127.0.0.1", port: 8100, path: `${url}?_rsc=audit`, headers: { Host: host } }, (res) => {
        const chunks = [];
        res.on("data", (chunk) => chunks.push(chunk));
        res.on("end", () => done({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks) }));
        res.on("error", fail);
      }).on("error", fail);
    });
    assert.equal(response.status, 200, `${panel}: ${url}`);
    assert.match(response.headers["content-type"], /^text\/plain/);
    assert.equal(response.headers["cache-control"], "no-cache");
    assert.deepEqual(response.body, readFileSync(file), `${panel}: wrong segment for ${url}`);
    count++;
  }
}
console.log(`${count} real flattened RSC prefetch requests passed across all five panels`);
