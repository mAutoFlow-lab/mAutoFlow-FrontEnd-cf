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

  // app 영역
  if (p === "/app/" || p.startsWith("/app/") || p.startsWith("/share/")) {
    url.pathname = "/app/index.html";
    return fetch(url.toString(), request);
  }

  // landing 영역 (pricing/terms/privacy 포함)
  url.pathname = "/index.html";
  return fetch(url.toString(), request);
}
