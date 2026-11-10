import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";

let pages = 0;
let assets = 0;
for (const panel of ["panel", "panel-admin", "panel-user", "panel-studio", "panel-toyxona"]) {
  const root = resolve("backend", panel);
  function visit(dir) {
    for (const item of readdirSync(dir, { withFileTypes: true })) {
      const file = join(dir, item.name);
      if (item.isDirectory() && item.name !== "_next") visit(file);
      else if (item.isFile() && item.name.endsWith(".html")) {
        pages++;
        const html = readFileSync(file, "utf8");
        for (const match of html.matchAll(/(?:src|href)="(\/_next\/[^"?]+)(?:\?[^"]*)?"/g)) {
          const rel = decodeURIComponent(match[1]);
          assert.ok(existsSync(join(root, rel)), `${panel}: missing ${rel}`);
          assets++;
        }
        if (item.name === "login.html") {
          // Some exported login routes render inside a client-only Suspense boundary.
          for (const [form] of html.matchAll(/<form\b[^>]*>/g)) {
            assert.match(form, /method="post"/, `${panel}: unsafe login form method`);
          }
        }
      }
    }
  }
  visit(root);
}
console.log(`${pages} HTML pages and ${assets} asset references verified`);
