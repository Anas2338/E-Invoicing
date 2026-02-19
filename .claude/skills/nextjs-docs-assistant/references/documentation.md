# Next.js Documentation Reference

This file contains detailed information about Next.js patterns, APIs, and best practices that should be referenced when working with Next.js code.

## App Router Structure

The App Router is the recommended way to build Next.js applications. Here's the complete directory structure with src directory:

```
src/
├── app/
│   ├── layout.tsx          # Root layout component (wraps all pages)
│   ├── page.tsx            # Home page (route: /)
│   ├── loading.tsx         # Loading UI (wraps all routes)
│   ├── error.tsx           # Error boundary (wraps all routes)
│   ├── not-found.tsx       # Not found page
│   ├── global-error.tsx    # Global error page (top-level)
│   ├── providers/          # Shared providers (optional)
│   │   └── index.tsx
│   ├── dashboard/
│   │   ├── layout.tsx      # Dashboard layout (route: /dashboard)
│   │   ├── page.tsx        # Dashboard page
│   │   ├── loading.tsx     # Dashboard loading UI
│   │   └── @.tsx          # Default route for dashboard
│   ├── blog/
│   │   ├── layout.tsx      # Blog layout (route: /blog)
│   │   ├── page.tsx        # Blog index page
│   │   ├── [slug]/
│   │   │   ├── page.tsx    # Dynamic blog post (route: /blog/:slug)
│   │   │   └── loading.tsx # Dynamic loading UI
│   │   └── draft/
│       └── page.tsx    # Draft page (route: /blog/draft)
│   ├── api/
│   │   └── route.ts        # API routes (route: /api/*)
│   └── (group)/            # Route groups (don't affect URL)
│       └── page.tsx
├── components/             # Shared components
│   └── ui/                # UI-specific components
└── lib/                   # Utility functions
    └── utils.ts
```

## File Conventions

### Layout Files
- `layout.tsx`: Shared UI for a route segment and its children
- Must accept `children` prop and return JSX with `children`
- Can contain `head.tsx` for segment-specific metadata

### Page Files
- `page.tsx`: UI for a specific route segment
- Can be either Server or Client Components
- Exported as default export

### Special Files
- `loading.tsx`: Loading UI for a route segment
- `error.tsx`: Error boundary for a route segment
- `not-found.tsx`: Not found UI for a route segment
- `global-error.tsx`: Global error boundary for the entire app
- `head.tsx`: Segment-specific metadata
- `template.tsx`: UI that is re-rendered for route changes

## Server Components

Server Components run on the server and can:
- Access backend resources (databases, APIs, file system)
- Include sensitive data or logic without exposing it to the client
- Import server-only libraries
- Use `async`/`await` for data fetching
- Import Client Components (but not vice versa)

```typescript
// Server Component example
async function DashboardPage() {
  const data = await fetch('https://api.example.com/dashboard')
  const user = await data.json()

  return (
    <div>
      <h1>Welcome, {user.name}</h1>
      <ClientComponent />
    </div>
  )
}

export default DashboardPage
```

## Client Components

Client Components run in the browser and can:
- Handle user interactions
- Maintain state with `useState`, `useEffect`, etc.
- Use browser APIs
- Must include `'use client'` directive at the top
- Can import and use Server Components (rendered before hydration)

```typescript
'use client'

import { useState } from 'react'

function Counter() {
  const [count, setCount] = useState(0)

  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
    </div>
  )
}

export default Counter
```

## Data Fetching Patterns

### Server Component Data Fetching

```typescript
// In a Server Component
async function UserPosts({ userId }: { userId: string }) {
  const res = await fetch(`https://jsonplaceholder.typicode.com/posts?userId=${userId}`)
  const posts: Post[] = await res.json()

  return (
    <div>
      {posts.map(post => (
        <article key={post.id}>
          <h2>{post.title}</h2>
          <p>{post.body}</p>
        </article>
      ))}
    </div>
  )
}

// With caching options
async function Product({ id }: { id: string }) {
  const res = await fetch(`https://api.example.com/products/${id}`, {
    next: { revalidate: 3600 }, // Revalidate every hour
  })
  const product = await res.json()

  return <div>{product.name}</div>
}
```

### Client Component Data Fetching

```typescript
'use client'

import { useState, useEffect } from 'react'
import { useSWR } from 'swr'

function UserProfile({ userId }: { userId: string }) {
  const { data, error } = useSWR(`/api/users/${userId}`, fetch)

  if (error) return <div>Failed to load</div>
  if (!data) return <div>Loading...</div>

  return <div>Hello {data.name}!</div>
}
```

## Server Actions

Server Actions allow you to execute server-side code from client components:

```typescript
// actions.ts
'use server'

import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'

export async function createPost(prevState: any, formData: FormData) {
  const title = formData.get('title') as string
  const content = formData.get('content') as string

  try {
    // Create post logic here
    await createPostInDatabase({ title, content })

    revalidatePath('/posts')
    redirect('/posts')
  } catch (error) {
    return { message: 'Failed to create post' }
  }
}

// In your component
import { createPost } from './actions'

export default function CreatePostForm() {
  return (
    <form action={createPost}>
      <input name="title" placeholder="Title" required />
      <textarea name="content" placeholder="Content" required />
      <button type="submit">Create Post</button>
    </form>
  )
}
```

## Route Handlers (API Routes)

```typescript
// app/api/users/route.ts
import { NextRequest } from 'next/server'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const id = searchParams.get('id')

  const user = await getUser(id)
  return Response.json({ user })
}

export async function POST(request: NextRequest) {
  const data = await request.json()
  const user = await createUser(data)
  return Response.json({ user }, { status: 201 })
}
```

## Dynamic Routes

```typescript
// app/products/[id]/page.tsx
type Props = {
  params: { id: string }
  searchParams: { [key: string]: string | string[] | undefined }
}

export default async function ProductPage({
  params,
  searchParams
}: Props) {
  const product = await fetchProduct(params.id)

  return (
    <div>
      <h1>{product.name}</h1>
      <p>Category: {searchParams.category}</p>
    </div>
  )
}

// For dynamic route generation
export async function generateStaticParams() {
  const products = await fetchProducts()

  return products.map((product) => ({
    id: product.id,
  }))
}
```

## Parallel and Intercepting Routes

### Parallel Routes
```typescript
// app/@analytics/page.tsx
export default function Analytics() {
  return <div>Analytics Panel</div>
}

// app/@dashboard/page.tsx
export default function Dashboard() {
  return <div>Dashboard Panel</div>
}

// app/layout.tsx
export default function Layout({
  children,
  analytics,
  dashboard,
}: {
  children: React.ReactNode
  analytics: React.ReactNode
  dashboard: React.ReactNode
}) {
  return (
    <>
      {children}
      {analytics}
      {dashboard}
    </>
  )
}
```

### Intercepting Routes
```typescript
// app/feed/@modal/(..)photo/[id]/page.tsx
// This intercepts the photo route and shows it in a modal
// instead of navigating to it
```

## Metadata

```typescript
// app/page.tsx
export const metadata = {
  title: 'Home',
  description: 'Welcome to Next.js',
}

// Dynamic metadata
// app/products/[id]/page.tsx
export async function generateMetadata({
  params,
}: {
  params: { id: string }
}): Promise<Metadata> {
  const product = await fetchProduct(params.id)

  return {
    title: product.name,
    description: product.description,
  }
}
```

## Error Handling

### Error Boundaries
```typescript
// app/error.tsx
'use client'

import { useEffect } from 'react'

export default function Error({
  error,
  reset,
}: {
  error: Error
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div>
      <h2>Something went wrong!</h2>
      <button
        onClick={
          () => reset()
        }
      >
        Try again
      </button>
    </div>
  )
}
```

## Loading UI

```typescript
// app/loading.tsx
export default function Loading() {
  return <div>Loading...</div>
}

// app/users/loading.tsx
export default function UsersLoading() {
  return <div>Loading users...</div>
}
```

## Navigation

```typescript
'use client'

import { usePathname, useSearchParams } from 'next/navigation'

export default function Component() {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  return <div>Current path: {pathname}</div>
}

// Programmatic navigation
'use client'

import { useRouter } from 'next/navigation'

export default function Button() {
  const router = useRouter()

  return (
    <button onClick={() => router.push('/dashboard')}>
      Go to Dashboard
    </button>
  )
}
```

## Image Optimization

```tsx
import Image from 'next/image'

export default function Page() {
  return (
    <Image
      src="/me.png"
      height={144}
      width={144}
      alt="Picture of the author"
      className="rounded-full"
    />
  )
}
```

## Environment Variables

```typescript
// .env.local
NEXT_PUBLIC_ANALYTICS_ID=abc123
DB_HOST=localhost
DB_PASS=super-secret-password

// In code
const analyticsId = process.env.NEXT_PUBLIC_ANALYTICS_ID
const dbHost = process.env.DB_HOST
```

## TypeScript Configuration

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "es6"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

## Common Patterns

### Form with Server Action and Validation
```typescript
'use server'

import { z } from 'zod'

const ContactFormSchema = z.object({
  name: z.string().min(1, { message: 'Name is required' }),
  email: z.string().email({ message: 'Invalid email' }),
  message: z.string().min(10, { message: 'Message must be at least 10 characters' }),
})

export type FormState = {
  errors?: {
    name?: string[]
    email?: string[]
    message?: string[]
  }
  message?: string | null
}

export async function contact(prevState: FormState, formData: FormData) {
  const validatedFields = ContactFormSchema.safeParse({
    name: formData.get('name'),
    email: formData.get('email'),
    message: formData.get('message'),
  })

  if (!validatedFields.success) {
    return {
      errors: validatedFields.error.flatten().fieldErrors,
      message: 'Missing Fields. Failed to Submit Form.',
    }
  }

  const { name, email, message } = validatedFields.data

  // Process the data (send email, save to DB, etc.)

  return { message: 'Form submitted successfully!' }
}

// Example component using the action (src/app/contact/page.tsx)
import { Button } from '@/components/ui/button'
import { contact, type FormState } from './actions'

export default function ContactForm() {
  const [state, formAction] = useFormState(contact, {
    message: null,
  })

  return (
    <form action={formAction}>
      <div>
        <label htmlFor="name">Name</label>
        <input
          id="name"
          name="name"
          type="text"
          required
        />
        {state?.errors?.name && (
          <span>{state.errors.name}</span>
        )}
      </div>

      <div>
        <label htmlFor="email">Email</label>
        <input
          id="email"
          name="email"
          type="email"
          required
        />
        {state?.errors?.email && (
          <span>{state.errors.email}</span>
        )}
      </div>

      <div>
        <label htmlFor="message">Message</label>
        <textarea
          id="message"
          name="message"
          required
        />
        {state?.errors?.message && (
          <span>{state.errors.message}</span>
        )}
      </div>

      <Button type="submit">Send Message</Button>

      {state?.message && <p>{state.message}</p>}
    </form>
  )
}
```

### Middleware
```typescript
// middleware.ts
import { NextRequest, NextResponse } from 'next/server'

export function middleware(request: NextRequest) {
  // Example: Redirect unauthenticated users
  if (request.nextUrl.pathname.startsWith('/dashboard')) {
    const token = request.cookies.get('auth-token')

    if (!token) {
      return NextResponse.redirect(new URL('/login', request.url))
    }
  }
}

export const config = {
  matcher: ['/dashboard/:path*', '/admin/:path*'],
}
```