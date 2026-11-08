// Builds the Super Admin panel as static files into backend/panel/, where Django serves it
// (api.marosimgo.uz = API + Super Admin panel in one deploy). Run: npm run build:panel
import { spawnSync } from "node:child_process";
import { cpSync, existsSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(root, "out");
const target = join(root, "..", "backend", "panel");

rmSync(out, { recursive: true, force: true });
const build = spawnSync("npx", ["next", "build"], {
  cwd: root,
  stdio: "inherit",
  shell: true,
  env: { ...process.env, PANEL_EXPORT: "1", NEXT_PUBLIC_PANEL_AUDIENCE: process.env.NEXT_PUBLIC_PANEL_AUDIENCE ?? "super_admin" },
});
if (build.status !== 0 || !existsSync(join(out, "index.html"))) process.exit(build.status || 1);

rmSync(target, { recursive: true, force: true });
cpSync(out, target, { recursive: true });
writeFileSync(join(target, "BUILD_INFO.txt"), `MarosimGo Super Admin panel — static build\nBuilt: ${new Date().toISOString()}\nDo not edit: regenerate with \`npm run build:panel\` in frontend/.\n`);
console.log(`\nPanel copied to ${target}`);
