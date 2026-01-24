export async function onRequest({ request, next }) {
  const url = new URL(request.url);

  // ✅ pages.dev로 들어온 요청만 301로 커스텀 도메인으로 이동
  if (url.hostname === "mautoflow-frontend-cf.pages.dev") {
    url.hostname = "mautoflow.com";
    url.protocol = "https:";
    return Response.redirect(url.toString(), 301);
  }

  // 커스텀 도메인(mautoflow.com)으로 들어오면 정상 처리
  return next();
}
