// Run against the disposable audit servers only. Tests actual proxying, CSRF and cookie isolation.
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";

const cases = [
  { port: 3100, role: "SUPER_ADMIN", phone: "+998901110001", paths: ["/api/v1/admin/platform-policy/", "/api/v1/users/", "/api/v1/admins/", "/api/v1/studios/", "/api/v1/admin/venues/", "/api/v1/admin/reviews/", "/api/v1/admin/subscriptions/", "/api/v1/admin/subscription-plans/", "/api/v1/admin/subscription-settings/", "/api/v1/dashboard/overview/", "/api/v1/admin/support/tickets/"] },
  { port: 3101, role: "USER", phone: "+998901110005", paths: ["/api/v1/me/ceremonies/", "/api/v1/me/invitations/", "/api/v1/me/subscriptions/status/", "/api/v1/me/venue-bookings/", "/api/v1/public/studios/", "/api/v1/venues/", "/api/v1/support/tickets/"] },
  { port: 3102, role: "STUDIO", phone: "+998901110003", paths: ["/api/v1/studios/me/", "/api/v1/studios/me/ceremonies/", "/api/v1/me/subscriptions/", "/api/v1/me/subscriptions/targets/", "/api/v1/support/tickets/"] },
  { port: 3103, role: "VENUE_OWNER", phone: "+998901110004", paths: ["/api/v1/venue-owner/venues/", "/api/v1/me/subscriptions/", "/api/v1/me/subscriptions/targets/", "/api/v1/support/tickets/"] },
];
const results = [];
for (const test of cases) {
  const origin = `http://127.0.0.1:${test.port}`;
  const jar = new Map();
  async function request(path, options = {}) {
    const response = await fetch(origin + path, {
      ...options, redirect: "manual",
      headers: { Origin: origin, Cookie: [...jar].map(([k, v]) => `${k}=${v}`).join("; "), ...options.headers },
    });
    assert.equal(response.status, 200, `${test.role} ${path}: ${response.status} ${response.headers.get("location") ?? ""}`);
    for (const cookie of response.headers.getSetCookie()) {
      const pair = cookie.split(";", 1)[0];
      const at = pair.indexOf("=");
      jar.set(pair.slice(0, at), pair.slice(at + 1));
    }
    const body = await response.json();
    results.push({ role: test.role, path, status: response.status });
    return body;
  }
  await request("/api/v1/auth/csrf/");
  const csrf = [...jar].find(([key]) => key.endsWith("csrftoken"))?.[1];
  assert.ok(csrf, "CSRF cookie must be proxied");
  const login = await request("/api/v1/auth/login/", { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf }, body: JSON.stringify({ phone_number: test.phone, password: "Local-Audit-2026!" }) });
  assert.equal(login.user.role, test.role);
  assert.equal((await request("/api/v1/auth/me/")).role, test.role);
  for (const path of test.paths) await request(path);
  if (test.role === "STUDIO" || test.role === "VENUE_OWNER") {
    const [target] = await request("/api/v1/me/subscriptions/targets/");
    assert.ok(target, "Expected a seeded business");
    const status = await request(`/api/v1/me/subscriptions/status/?${target.kind}=${target.id}`);
    assert.equal(status.is_verified, true, "Paid business badge must be active");
    assert.equal(status.clean_access, false, "Business badges must not grant personal media access");
  }
  console.log(`${test.role}: proxy, CSRF, login, cookies and ${test.paths.length} API reads passed`);
}
await mkdir(".qa", { recursive: true });
await writeFile(".qa/api-smoke-results.json", JSON.stringify(results, null, 2) + "\n");
console.log(`${results.length} HTTP checks passed`);
