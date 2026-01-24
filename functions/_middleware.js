export async function onRequest({ request, next }) {
  const url = new URL(request.url);

  // pages.dev → mautoflow.com 301
  if (url.hostname === "mautoflow-frontend-cf.pages.dev") {
    url.hostname = "mautoflow.com";
    url.protocol = "https:";
    return Response.redirect(url.toString(), 301);
  }

  const p = url.pathname;

  // ✅ (추가) LEGAL 3종은 무조건 app/index.html로 서빙
  if (
    p === "/pricing" ||
    p === "/terms-of-service" ||
    p === "/privacy-policy" ||
    p === "/terms" ||            // 호환용
    p === "/privacy"             // 호환용
  ) {
    url.pathname = "/app/index.html";
    return fetch(url.toString(), request);
  }

  const res = await next();
  if (res.status !== 404) return res;

  // app 영역
  if (p === "/app/" || p.startsWith("/app/") || p.startsWith("/share/")) {
    url.pathname = "/app/index.html";
    return fetch(url.toString(), request);
  }

  // landing 영역
  url.pathname = "/index.html";
  return fetch(url.toString(), request);
}
