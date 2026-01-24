export async function onRequest({ request, next }) {
  const url = new URL(request.url);

  // pages.dev → mautoflow.com 301
  if (url.hostname === "mautoflow-frontend-cf.pages.dev") {
    url.hostname = "mautoflow.com";
    url.protocol = "https:";
    return Response.redirect(url.toString(), 301);
  }

  const res = await next();
  if (res.status !== 404) return res;

  const p = url.pathname;

  // ✅ legal은 app SPA로 rewrite
  const LEGAL_PATHS = new Set(["/terms-of-service", "/privacy-policy"]);
  if (LEGAL_PATHS.has(p)) {
    url.pathname = "/app/index.html";
    return fetch(url.toString(), request);
  }

  // app 영역
  if (p === "/app/" || p.startsWith("/app/") || p.startsWith("/share/")) {
    url.pathname = "/app/index.html";
    return fetch(url.toString(), request);
  }

  // landing 영역 (pricing 등)
  url.pathname = "/index.html";
  return fetch(url.toString(), request);
}
