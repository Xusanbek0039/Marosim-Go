// Builds the user cabinet as static files into backend/panel-user/, where Django serves it on
// userlogin.marosimgo.uz (one cPanel deploy with the API — see backend/config/panel.py).
// Run: npm run build:panel
import { spawnSync } from "node:child_process";
import { cpSync, existsSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(root, "out");
const target = join(root, "..", "backend", "panel-user");

rmSync(out, { recursive: true, force: true });
const build = spawnSync(process.platform === "win32" ? "npx.cmd next build" : "npx next build", {
  cwd: root,
  stdio: "inherit",
  shell: true,
  env: { ...process.env, PANEL_EXPORT: "1" },
});
if (build.status !== 0 || !existsSync(join(out, "index.html"))) process.exit(build.status || 1);

rmSync(target, { recursive: true, force: true });
cpSync(out, target, { recursive: true });
writeFileSync(
  join(target, ".gitattributes"),
  "# Built files: keep the bytes exactly as Next.js wrote them (RSC payloads contain byte lengths).\n* -text\n",
);
writeFileSync(
  join(target, "BUILD_INFO.txt"),
  `MarosimGo User cabinet — static build\nBuilt: ${new Date().toISOString()}\nDo not edit: regenerate with \`npm run build:panel\` in frontend-user/.\n`,
);
console.log(`\nUser cabinet copied to ${target}`);
