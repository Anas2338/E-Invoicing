import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

/**
 * Server Component root route.
 *
 * Reads the httpOnly `access_token` cookie (set by the backend on login) and
 * issues a real HTTP redirect, so crawlers and direct requests to `/` get a
 * 307 instead of a 200 that only redirects once client JS runs.
 *
 * Note: `cookies()` is async in Next.js 15+ and must be awaited.
 */
export default async function HomePage() {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get('access_token')?.value;

  // An expired/invalid token is caught by the (protected) layout, which
  // bounces the user back to /login after its profile check fails.
  redirect(accessToken ? '/dashboard' : '/login');
}
