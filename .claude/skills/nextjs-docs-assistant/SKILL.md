---
name: nextjs-docs-assistant
description: Assists with writing Next.js applications using the latest official Next.js documentation. Enforces App Router–first, server-first architecture, defaults to Server Components, uses "use client" only when required, prefers server actions, and follows current documented patterns with no legacy assumptions.
allowed-tools: Read, Grep, Glob
---

# Next.js Docs Assistant

This skill assists with writing Next.js applications based strictly on the latest official Next.js documentation. It enforces App Router–first, server-first architecture, defaults to Server Components, uses "use client" only when required, prefers Server Actions, and follows current documented patterns with no legacy assumptions.

## What This Skill Does

- Enforces App Router–first, server-first architecture by default
- Recommends Server Components as the default approach
- Uses "use client" directive only when client-side interactivity is required
- Promotes Server Actions for server-side mutations
- Implements current rendering strategies (SSR, SSG, ISR, streaming)
- Provides accurate API usage based on current documentation
- Recommends modern patterns and avoids legacy approaches

## When to Use This Skill

Use when creating or modifying Next.js code, especially within the `app/` directory. The skill auto-activates for Next.js development and enforces modern, server-first architecture.

## Before Implementation

Gather context to ensure successful implementation:

| Source | Gather |
|--------|--------|
| **Codebase** | Current Next.js project structure, existing patterns and conventions in `app/` directory |
| **Conversation** | User's specific Next.js requirements and constraints |
| **Official Docs** | Current Next.js documentation patterns from `references/` |
| **User Guidelines** | Project-specific conventions and requirements |

Ensure all required context is gathered before implementing.

## App Router Architecture

The App Router is the recommended and current approach for Next.js applications:

```
app/
├── layout.tsx              # Root layout (Server Component by default)
├── page.tsx               # Homepage route (Server Component by default)
├── @modal/(.)folder/      # Parallel routes
├── (group)/               # Route groups
├── [...slug]/             # Catch-all segments
├── [[...slug]]/           # Optional catch-all segments
├── providers/             # Shared providers
├── error.tsx              # Global error boundary
├── loading.tsx            # Global loading UI
├── not-found.tsx          # Global not found page
└── dashboard/
    ├── layout.tsx         # Nested layout (Server Component)
    ├── loading.tsx        # Loading UI for nested routes
    ├── error.tsx          # Error boundary for nested routes
    └── page.tsx          # Dashboard page (Server Component)
```

### Route Segments

- `(group)` - Route groups for organizing without affecting URL structure
- `[slug]` - Dynamic segments
- `[...slug]` - Catch-all segments
- `[[...slug]]` - Optional catch-all segments
- `@slot` - Parallel routes
- `(..)` - Back to parent directory

## Server Components (Default)

Server Components are the default and preferred approach. They run only on the server and can contain child Server or Client Components:

```tsx
// app/users/page.tsx - Server Component by default
import UserCard from '@/components/user-card'

export default async function UsersPage() {
  // Data fetching happens on the server
  const res = await fetch('https://api.example.com/users')
  const users = await res.json()

  return (
    <div>
      {users.map(user => (
        <UserCard key={user.id} user={user} />
      ))}
    </div>
  )
}
```

## Client Components (Required Only)

Use "use client" directive only when client-side interactivity is required:

```tsx
'use client'

import { useState, useEffect } from 'react'

export default function InteractiveCounter() {
  const [count, setCount] = useState(0)

  useEffect(() => {
    // Client-side effects only
    document.title = `Count: ${count}`
  }, [count])

  return (
    <button onClick={() => setCount(count + 1)}>
      Count: {count}
    </button>
  )
}
```

## Data Fetching Patterns

### Server-Side Fetching (Preferred)

Perform data fetching directly in Server Components using native fetch:

```tsx
// app/products/page.tsx
export default async function ProductsPage() {
  const res = await fetch('https://api.example.com/products')
  const products = await res.json()

  return (
    <div>
      {products.map(product => (
        <div key={product.id}>{product.name}</div>
      ))}
    </div>
  )
}
```

### Static Generation (Default Behavior)

By default, fetch requests are cached until manually invalidated:

```tsx
// app/blog/page.tsx
export default async function BlogPage() {
  // This fetch is automatically cached (equivalent to force-cache)
  const posts = await fetch('https://api.example.com/posts').then(r => r.json())

  return <BlogList posts={posts} />
}
```

### Dynamic Fetching

Force dynamic fetching on every request:

```tsx
// app/dashboard/page.tsx
export default async function DashboardPage() {
  // This fetch bypasses cache (equivalent to getServerSideProps)
  const data = await fetch('https://api.example.com/data', {
    cache: 'no-store'
  }).then(r => r.json())

  return <Dashboard data={data} />
}
```

### Incremental Static Regeneration (ISR)

Revalidate data after a specified time:

```tsx
// app/products/page.tsx
export default async function ProductsPage() {
  // This fetch will revalidate every 10 seconds (equivalent to getStaticProps with revalidate)
  const products = await fetch('https://api.example.com/products', {
    next: { revalidate: 10 }
  }).then(r => r.json())

  return <ProductList products={products} />
}
```

### Streaming with Suspense

Enable streaming responses for better performance:

```tsx
// app/dashboard/page.tsx
import { Suspense } from 'react'
import Feed from './feed'
import Sidebar from './sidebar'

export default function DashboardPage() {
  return (
    <div className="flex">
      <Suspense fallback={<p>Loading sidebar...</p>}>
        <Sidebar />
      </Suspense>
      <Suspense fallback={<p>Loading feed...</p>}>
        <Feed />
      </Suspense>
    </div>
  )
}
```

## Server Actions

Use Server Actions for server-side mutations instead of API routes:

```tsx
// app/actions/user-actions.ts
'use server'

import { revalidatePath } from 'next/cache'

export async function createUser(prevState: any, formData: FormData) {
  try {
    const name = formData.get('name') as string
    const email = formData.get('email') as string

    // Perform server-side logic
    await db.users.create({ name, email })

    // Revalidate path after mutation
    revalidatePath('/users')

    return { success: true }
  } catch (error) {
    return { error: 'Failed to create user' }
  }
}
```

```tsx
// app/users/create-form.tsx
'use client'

import { useFormState } from 'react-dom'
import { createUser } from '@/actions/user-actions'

export default function CreateUserForm() {
  const [state, formAction] = useFormState(createUser, null)

  return (
    <form action={formAction}>
      <input name="name" placeholder="Name" required />
      <input name="email" type="email" placeholder="Email" required />
      <button type="submit">Create User</button>
      {state?.error && <p>{state.error}</p>}
    </form>
  )
}
```

## Route Handlers

Create API endpoints using Route Handlers in the `app/` directory:

```ts
// app/api/users/route.ts
import { NextRequest } from 'next/server'

export async function GET(request: NextRequest) {
  // Access query parameters
  const searchParams = request.nextUrl.searchParams
  const id = searchParams.get('id')

  const users = await getUsers(id ? { id } : {})
  return Response.json(users)
}

export async function POST(request: NextRequest) {
  const data = await request.json()
  const user = await createUser(data)
  return Response.json(user)
}

// Route segment configuration
export const dynamic = 'force-dynamic'
export const revalidate = 3600
```

## Rendering Strategies Configuration

Configure rendering behavior at the segment level:

```ts
// app/api/endpoint/route.ts or app/page.tsx
export const dynamic = 'auto'           // 'auto' | 'force-dynamic' | 'error' | 'force-static'
export const dynamicParams = true       // Whether to allow dynamic params
export const revalidate = false         // Seconds to revalidate, false to disable
export const fetchCache = 'auto'        // 'auto' | 'force-no-store' | 'only-cache' | 'default-cache'
export const runtime = 'nodejs'         // 'nodejs' | 'edge'
export const preferredRegion = 'auto'   // Region preference
```

## Image Optimization

Use the Next.js Image component for optimized images:

```tsx
import Image from 'next/image'

export default function HeroSection() {
  return (
    <Image
      src="/images/hero.jpg"
      alt="Hero image"
      width={800}
      height={500}
      priority // For above-the-fold images
    />
  )
}
```

## Font Optimization

Use next/font for font optimization:

```tsx
// app/layout.tsx
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={inter.className}>
      <body>{children}</body>
    </html>
  )
}
```

## Script Component

Use the Script component for third-party scripts:

```tsx
import Script from 'next/script'

export default function AnalyticsPage() {
  return (
    <>
      <h1>Analytics Dashboard</h1>
      <Script
        src="https://example.com/analytics.js"
        strategy="afterInteractive"
        onLoad={() => console.log('Analytics loaded')}
      />
    </>
  )
}
```

## Environment Variables

Use environment variables for configuration:

```env
# .env.local
NEXT_PUBLIC_SITE_URL=https://example.com
DATABASE_URL=postgresql://user:pass@localhost:5432/db
```

```ts
// Access in server components
const apiUrl = process.env.DATABASE_URL
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL
```

## Middleware

Handle requests before they reach the route:

```ts
// middleware.ts
import { NextRequest, NextResponse } from 'next/server'

export function middleware(request: NextRequest) {
  // Redirect logic
  if (request.nextUrl.pathname === '/old-path') {
    return NextResponse.redirect(new URL('/new-path', request.url))
  }

  // Authentication check
  const token = request.cookies.get('token')
  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
}

// Apply to specific paths
export const config = {
  matcher: ['/dashboard/:path*', '/api/:path*'],
}
```

## TypeScript Support

Next.js has built-in TypeScript support. Simply rename files to `.ts` or `.tsx`:

```tsx
// app/users/[id]/page.tsx
type User = {
  id: string
  name: string
  email: string
}

export default async function UserPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const user: User = await fetchUser(id)

  return <UserProfile user={user} />
}
```

## Runtimes

Specify runtime for specific segments:

```ts
// app/api/edge-function/route.ts
export const runtime = 'edge' // 'nodejs' (default) | 'edge'

export async function GET() {
  // Runs in edge environment
  return new Response('Hello from edge!')
}
```

## Deployment Guidance

### Production Build
```bash
npm run build
npm start
```

### Environment Configuration
- Use `NEXT_PUBLIC_` prefix for client-side accessible variables
- Set environment variables in deployment platform
- Use different .env files for different environments

### Performance Optimization
- Leverage automatic image optimization
- Use streaming and Suspense for better loading experiences
- Implement proper caching strategies
- Use dynamic imports for code splitting

## Best Practices Summary

- **Server-First Architecture**: Default to Server Components
- **Client Components**: Use "use client" only when client-side interactivity is required
- **Data Fetching**: Perform in Server Components using native fetch
- **Server Actions**: Use for server-side mutations instead of API routes
- **Streaming**: Implement Suspense boundaries for better UX
- **Caching**: Leverage Next.js caching strategies appropriately
- **TypeScript**: Use for type safety throughout the application
- **Modern Patterns**: Follow current documentation, avoid legacy approaches