// NEXUS scheduler: only *triggers* the backend. No AI / long work here.
async function sign(secret, message) {
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message));
  return [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, "0")).join("");
}

async function callBackend(env, path, body = {}) {
  const ts = Math.floor(Date.now() / 1000).toString();
  const payload = JSON.stringify(body);
  const signature = await sign(env.WORKER_AUTH_SECRET, `${ts}..${payload}`);
  // Render free tier may sleep ~1 min: retry with backoff.
  let last;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await fetch(env.BACKEND_URL + path, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Nexus-Timestamp": ts,
          "X-Nexus-Signature": signature,
          
        },
        body: payload,
      });
      if (res.ok) return { ok: true, status: res.status };
      last = { ok: false, status: res.status };
      if (res.status < 500) break;
    } catch (e) {
      last = { ok: false, error: String(e) };
    }
    await new Promise(r => setTimeout(r, 5000 * (attempt + 1)));
  }
  return last;
}

export default {
  async scheduled(event, env, ctx) {
    const path = "/api/webhooks/cron/news-scan";
    ctx.waitUntil(callBackend(env, path, { trigger: "cloudflare_cron", cron: event.cron }));
  },
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/health") return Response.json({ worker: "online" });
    return new Response("Not found", { status: 404 });
  },
};
