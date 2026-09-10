import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Root-route redirect.
 *
 * This runs as a proxy, before rendering, so it returns a real HTTP 307 with
 * a `Location` header. Calling `redirect()` from a streamed Server Component
 * cannot set the status code — Next.js falls back to an HTTP 200 carrying
 * `<meta http-equiv="refresh">`, which is invisible to crawlers and adds a
 * visible delay for users.
 *
 * Next.js 16 renamed this file convention from `middleware` to `proxy`,
 * along with the exported function name.
 */
export function proxy(request: NextRequest) {
  const accessToken = request.cookies.get('access_token')?.value;
  const url = request.nextUrl.clone();

  // An expired or invalid token is caught by the (protected) layout, which
  // bounces the user back to /login once its profile check fails.
  url.pathname = accessToken ? '/dashboard' : '/login';

  return NextResponse.redirect(url);
}

export const config = {
  // Only the root path — every other route is handled by the app itself.
  matcher: '/',
};
