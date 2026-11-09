// Existing same-origin partner API and HTTP-LAN compatible proof of work.
(()=>{
  // ---------------------------------------- anti-bot proof-of-work (SHA-256)
  // Pure JS on purpose: crypto.subtle only exists on HTTPS / localhost, the LAN demo runs on plain HTTP.
  const K = new Uint32Array([0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]);
  const W64 = new Uint32Array(64);
  function sha256(bytes) {
    const H = new Uint32Array([0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]);
    const l = bytes.length, nb = ((l + 9 + 63) >> 6) << 6, m = new Uint8Array(nb);
    m.set(bytes); m[l] = 0x80;
    const bits = l * 8;
    m[nb - 4] = bits >>> 24; m[nb - 3] = (bits >>> 16) & 255; m[nb - 2] = (bits >>> 8) & 255; m[nb - 1] = bits & 255;
    for (let o = 0; o < nb; o += 64) {
      for (let i = 0; i < 16; i++) W64[i] = (m[o + 4 * i] << 24) | (m[o + 4 * i + 1] << 16) | (m[o + 4 * i + 2] << 8) | m[o + 4 * i + 3];
      for (let i = 16; i < 64; i++) {
        const a = W64[i - 15], b = W64[i - 2];
        const s0 = ((a >>> 7) | (a << 25)) ^ ((a >>> 18) | (a << 14)) ^ (a >>> 3);
        const s1 = ((b >>> 17) | (b << 15)) ^ ((b >>> 19) | (b << 13)) ^ (b >>> 10);
        W64[i] = (W64[i - 16] + s0 + W64[i - 7] + s1) | 0;
      }
      let a = H[0], b = H[1], c = H[2], d = H[3], e = H[4], f = H[5], g = H[6], h = H[7];
      for (let i = 0; i < 64; i++) {
        const S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
        const t1 = (h + S1 + ((e & f) ^ (~e & g)) + K[i] + W64[i]) | 0;
        const S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
        const t2 = (S0 + ((a & b) ^ (a & c) ^ (b & c))) | 0;
        h = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
      }
      H[0] += a; H[1] += b; H[2] += c; H[3] += d; H[4] += e; H[5] += f; H[6] += g; H[7] += h;
    }
    return H;
  }
  const zeroBits = (H) => (H[0] ? Math.clz32(H[0]) : 32 + Math.clz32(H[1]));
  const enc = new TextEncoder();
  async function solve(token, difficulty) {
    const prefix = token + ":";
    for (let n = 0; ; n++) {
      if (zeroBits(sha256(enc.encode(prefix + n))) >= difficulty) return String(n);
      if (n % 3000 === 2999) await new Promise((r) => setTimeout(r, 0)); // keep the page responsive
    }
  }

  // ------------------------------------------- partner application form
  const API = "/api/v1/public/partner-applications/";
  const form = document.getElementById("apply-form");
  const check = document.getElementById("bot-check");
  const checkText = check.querySelector("span");
  const businessLabel = document.getElementById("a-business-label");
  let kind = "STUDIO", pending = null, submitting = false, retryAfter = 0;

  const setCheck = (state, text) => { check.dataset.state = state; checkText.textContent = text; };
  function prepare() {
    if (pending) return pending;
    setCheck("working", "Robot emasligingiz tekshirilmoqda...");
    pending = fetch(API + "challenge/", { headers: { Accept: "application/json" }, cache: "no-store", signal: AbortSignal.timeout(15000) })
      .then((r) => (r.ok ? r.json() : Promise.reject(r)))
      .then(async (ch) => {
        if (typeof ch.token !== "string" || ch.token.length > 500 || !Number.isInteger(ch.difficulty) || ch.difficulty < 0 || ch.difficulty > 20 || !Number.isFinite(ch.min_seconds) || ch.min_seconds < 0 || ch.min_seconds > 60) throw new Error("Invalid challenge");
        const issued = Date.now();
        const proof = await solve(ch.token, ch.difficulty);
        setCheck("ok", "Tekshiruvdan o'tdingiz");
        return { token: ch.token, proof, readyAt: issued + ch.min_seconds * 1000 + 250 };
      })
      .catch(() => { setCheck("idle", "Ulanishni tekshirib bo‘lmadi. Yuborishda qayta urinamiz."); pending = null; retryAfter = Date.now() + 15000; return null; });
    return pending;
  }
  if ("IntersectionObserver" in window) {
    new IntersectionObserver((e, o) => { if (e[0].isIntersecting) { o.disconnect(); if (!pending) prepare(); } }, { rootMargin: "300px" }).observe(form);
  }
  form.addEventListener("focusin", () => { if (!pending && Date.now() > retryAfter) prepare(); });

  form.querySelectorAll("[data-kind]").forEach((chip) => chip.addEventListener("click", () => {
    kind = chip.dataset.kind;
    form.querySelectorAll("[data-kind]").forEach((c) => c.setAttribute("aria-pressed", String(c === chip)));
    businessLabel.textContent = kind === "VENUE" ? "To‘yxona nomi " : "Studiya nomi ";
    const requiredMark = document.createElement("span"); requiredMark.textContent = "*"; businessLabel.append(requiredMark);
  }));
  const showErrors = (errors) => {
    form.querySelectorAll(".err[data-for]").forEach((el) => { el.textContent = ""; });
    form.querySelectorAll("[aria-invalid]").forEach((el) => el.removeAttribute("aria-invalid"));
    Object.entries(errors).forEach(([field, messages]) => {
      const box = [...form.querySelectorAll('.err[data-for]')].find(el => el.dataset.for === field) || form.querySelector('.err[data-for="_form"]');
      box.textContent = [].concat(messages).join(" ");
      if (form.elements[field]) form.elements[field].setAttribute("aria-invalid", "true");
    });
  };
  const button = form.querySelector('button[type="submit"]');
  const label = button.querySelector(".label");
  const busy = (on, text) => { button.disabled = on; button.classList.toggle("busy", on); label.textContent = text || "Ariza yuborish"; };

  async function send(data, digits, retried) {
    const pass = await (pending || prepare());
    if (!pass) throw new Error("challenge");
    const wait = pass.readyAt - Date.now();
    if (wait > 0) await new Promise((r) => setTimeout(r, wait));
    pending = null; // a token is good for one application only
    const res = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(Object.assign({}, data, { kind, phone_number: "+998" + digits, challenge: pass.token, proof: pass.proof })),
      signal: AbortSignal.timeout(20000),
    });
    if (res.status === 201) {
      const receipt = await res.json().catch(() => null);
      if (receipt?.received === true) return { ok: true };
      return { ok: false, status: res.status, error: { message: "Server javobi kutilgan formatda emas. Qayta urinib ko‘ring." } };
    }
    const body = await res.json().catch(() => ({}));
    const error = body.error || {};
    if (res.status === 403 && error.code === "bot_check_failed" && !retried) { prepare(); return send(data, digits, true); }
    return { ok: false, status: res.status, error };
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (submitting) return;
    const data = Object.fromEntries(new FormData(form));
    let digits = data.phone_number.replace(/\D/g, "");
    if (digits.length === 12 && digits.startsWith("998")) digits = digits.slice(3);
    data.full_name = data.full_name.trim(); data.business_name = data.business_name.trim(); data.message = data.message.trim();
    const local = {};
    if (!data.full_name.trim()) local.full_name = "Ismingizni yozing.";
    if (digits.length !== 9) local.phone_number = "9 ta raqam kiriting, masalan 90 123 45 67.";
    if (!data.business_name.trim()) local.business_name = kind === "VENUE" ? "To'yxona nomini yozing." : "Studiya nomini yozing.";
    showErrors(local);
    if (Object.keys(local).length) { form.elements[Object.keys(local)[0]].focus(); return; }
    submitting = true; form.setAttribute("aria-busy", "true");
    busy(true, "Yuborilmoqda...");
    try {
      const result = await send(data, digits, false);
      if (result.ok) { form.classList.add("sent"); form.querySelector(".form-content").hidden = true; form.querySelector(".done").hidden = false; form.querySelector(".done").focus(); return; }
      if (result.status === 429) showErrors({ _form: "Juda ko'p urinish. Birozdan keyin qayta yuboring." });
      else showErrors(result.error.details || { _form: result.error.message || "Yuborib bo'lmadi. Qayta urinib ko'ring." });
      prepare(); // a fresh one-time token for the next try
    } catch (err) {
      showErrors({ _form: "Server bilan bog‘lanib bo‘lmadi. Internet aloqasini tekshirib, qayta urinib ko‘ring." });
      pending = null;
    } finally {
      busy(false);
      submitting = false; form.removeAttribute("aria-busy");
    }
  });
})();
