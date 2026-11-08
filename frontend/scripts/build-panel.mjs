// Builds a panel as static files into backend/, where Django serves it on its own subdomain
// (one cPanel deploy with the API — see backend/config/panel.py):
//   npm run build:panel        → Super Admin → backend/panel/        (superadmin.marosimgo.uz)
//   npm run build:panel:admin  → Admin       → backend/panel-admin/  (admin.marosimgo.uz)
import { spawnSync } from "node:child_process";
import { cpSync, existsSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(root, "out");
const audience = process.argv[2] === "admin" ? "admin" : "super_admin";
const label = audience === "admin" ? "Admin" : "Super Admin";
const target = join(root, "..", "backend", audience === "admin" ? "panel-admin" : "panel");

rmSync(out, { recursive: true, force: true });
const build = spawnSync(process.platform === "win32" ? "npx.cmd next build" : "npx next build", {
  cwd: root,
  stdio: "inherit",
  shell: true,
  env: { ...process.env, PANEL_EXPORT: "1", NEXT_PUBLIC_PANEL_AUDIENCE: audience },
});
if (build.status !== 0 || !existsSync(join(out, "index.html"))) process.exit(build.status || 1);

rmSync(target, { recursive: true, force: true });
cpSync(out, target, { recursive: true });
writeFileSync(
  join(target, ".gitattributes"),
  "# Built files: keep the bytes exactly as Next.js wrote them (RSC payloads contain byte lengths).\n* -text\n",
);
const command = audience === "admin" ? "build:panel:admin" : "build:panel";
writeFileSync(
  join(target, "BUILD_INFO.txt"),
  `MarosimGo ${label} panel — static build\nBuilt: ${new Date().toISOString()}\nDo not edit: regenerate with \`npm run ${command}\` in frontend/.\n`,
);
console.log(`\n${label} panel copied to ${target}`);
