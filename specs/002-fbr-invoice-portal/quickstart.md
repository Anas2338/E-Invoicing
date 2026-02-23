# Quickstart Guide: FBR Invoice Portal Frontend

**Feature**: 002-fbr-invoice-portal
**Date**: 2026-02-23
**Estimated Setup Time**: 30-45 minutes

## Prerequisites

- Node.js 18+ installed
- npm or yarn package manager
- Git
- Backend API running (see backend documentation)
- Code editor (VS Code recommended)

---

## Step 1: Project Setup

### 1.1 Create Next.js Project

```bash
npx create-next-app@latest fbr-invoice-portal --typescript --tailwind --app --no-src-dir
cd fbr-invoice-portal
```

**Configuration prompts**:
- TypeScript: Yes
- ESLint: Yes
- Tailwind CSS: Yes (will install 4.1)
- App Router: Yes
- Import alias: Yes (@/*)

**Note**: This will install Next.js 16+ and Tailwind CSS 4.1 by default.

### 1.2 Install Dependencies

```bash
# UI Components
npx shadcn@latest init

# State Management
npm install @tanstack/react-query @tanstack/react-query-devtools

# Form Handling
npm install react-hook-form zod @hookform/resolvers

# Authentication
npm install better-auth

# Data Tables
npm install @tanstack/react-table

# Date Handling
npm install date-fns

# Utilities
npm install clsx tailwind-merge
```

### 1.3 Install shadcn/ui Components

```bash
npx shadcn@latest add button input label form table toast dialog card select
```

---

## Step 2: Environment Configuration

### 2.1 Create Environment Files

**`.env.local`**:
```env
# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Better Auth
NEXT_PUBLIC_BETTER_AUTH_URL=http://localhost:3000
BETTER_AUTH_SECRET=your-secret-key-here-min-32-chars
DATABASE_URL=postgresql://user:password@localhost:5432/fbr_portal

# Environment
NODE_ENV=development
```

**`.env.production`**:
```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_BETTER_AUTH_URL=https://yourdomain.com
BETTER_AUTH_SECRET=production-secret-key
DATABASE_URL=postgresql://user:password@production-host:5432/fbr_portal
NODE_ENV=production
```

### 2.2 Update `.gitignore`

```gitignore
# Environment files
.env*.local
.env.production

# Dependencies
node_modules/

# Next.js
.next/
out/

# Debug
npm-debug.log*
yarn-debug.log*
yarn-error.log*
```

---

## Step 3: Project Structure

### 3.1 Create Folder Structure

```bash
mkdir -p app/{(auth),(dashboard)}/{login,signup,dashboard,invoices,settings}
mkdir -p app/_components/{ui,features,shared}
mkdir -p app/_lib/{api,auth,utils,hooks}
mkdir -p app/api/{auth,proxy}
```

### 3.2 Folder Structure Overview

```
app/
├── (auth)/
│   ├── login/
│   │   └── page.tsx
│   ├── signup/
│   │   └── page.tsx
│   └── layout.tsx
├── (dashboard)/
│   ├── dashboard/
│   │   └── page.tsx
│   ├── invoices/
│   │   ├── page.tsx
│   │   ├── new/
│   │   │   └── page.tsx
│   │   └── [id]/
│   │       └── page.tsx
│   ├── settings/
│   │   └── page.tsx
│   └── layout.tsx
├── api/
│   ├── auth/
│   │   └── [...all]/
│   │       └── route.ts
│   └── proxy/
│       └── [...path]/
│           └── route.ts
├── _components/
│   ├── ui/              # shadcn/ui components
│   ├── features/        # Feature-specific components
│   └── shared/          # Shared components
├── _lib/
│   ├── api/             # API client
│   ├── auth/            # Auth configuration
│   ├── utils/           # Utility functions
│   └── hooks/           # Custom hooks
├── layout.tsx
├── page.tsx
└── globals.css
```

---

## Step 4: Better Auth Setup

### 4.1 Create Auth Instance

**`app/_lib/auth/auth.ts`**:
```typescript
import { betterAuth } from "better-auth"

export const auth = betterAuth({
  database: {
    provider: "postgres",
    url: process.env.DATABASE_URL!,
  },
  baseURL: process.env.BETTER_AUTH_URL!,
  advanced: {
    useSecureCookies: process.env.NODE_ENV === "production",
    defaultCookieAttributes: {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax"
    }
  }
})
```

### 4.2 Create API Route Handler

**`app/api/auth/[...all]/route.ts`**:
```typescript
import { auth } from "@/app/_lib/auth/auth"
import { toNextJsHandler } from "better-auth/next-js"

export const { POST, GET } = toNextJsHandler(auth)
```

### 4.3 Create Auth Client

**`app/_lib/auth/auth-client.ts`**:
```typescript
import { createAuthClient } from "better-auth/react"

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_BETTER_AUTH_URL!,
})

export const { signIn, signUp, signOut, useSession } = authClient
```

### 4.4 Create Middleware

**`middleware.ts`** (root level):
```typescript
import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/app/_lib/auth/auth"
import { headers } from "next/headers"

export async function middleware(request: NextRequest) {
  const session = await auth.api.getSession({
    headers: await headers()
  })

  const { pathname } = request.nextUrl

  // Protect dashboard routes
  if (pathname.startsWith("/dashboard") || pathname.startsWith("/invoices")) {
    if (!session) {
      return NextResponse.redirect(new URL("/login", request.url))
    }
  }

  // Redirect authenticated users from auth pages
  if (pathname.startsWith("/login") || pathname.startsWith("/signup")) {
    if (session) {
      return NextResponse.redirect(new URL("/dashboard", request.url))
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/dashboard/:path*", "/invoices/:path*", "/login", "/signup"]
}
```

---

## Step 5: React Query Setup

### 5.1 Create Query Client Provider

**`app/_components/providers/query-provider.tsx`**:
```typescript
"use client"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ReactQueryDevtools } from "@tanstack/react-query-devtools"
import { useState } from "react"

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        cacheTime: 10 * 60 * 1000,
        refetchOnWindowFocus: false,
        retry: 1,
      },
    },
  }))

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
```

### 5.2 Add Provider to Root Layout

**`app/layout.tsx`**:
```typescript
import { QueryProvider } from "./_components/providers/query-provider"
import "./globals.css"

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          {children}
        </QueryProvider>
      </body>
    </html>
  )
}
```

---

## Step 6: API Client Setup

### 6.1 Create API Client

**`app/_lib/api/client.ts`**:
```typescript
export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public code: string,
    public details?: any
  ) {
    super(message)
    this.name = "APIError"
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${process.env.NEXT_PUBLIC_API_URL}/api/v1${endpoint}`

  const response = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new APIError(
      error.error.message,
      error.error.status,
      error.error.code,
      error.error.details
    )
  }

  return response.json()
}
```

---

## Step 7: Run Development Server

```bash
npm run dev
```

Visit: http://localhost:3000

---

## Step 8: Verify Setup

### 8.1 Check Environment Variables

```bash
# Verify .env.local is loaded
npm run dev
# Should see no errors about missing environment variables
```

### 8.2 Test Authentication

1. Navigate to http://localhost:3000/signup
2. Create a test account
3. Verify redirect to dashboard
4. Check browser cookies for session token

### 8.3 Test API Connection

1. Open browser DevTools (Network tab)
2. Navigate to dashboard
3. Verify API requests to backend
4. Check for CORS errors (should be none)

---

## Common Issues & Solutions

### Issue: "Module not found" errors

**Solution**:
```bash
rm -rf node_modules package-lock.json
npm install
```

### Issue: Better Auth database errors

**Solution**:
```bash
# Run Better Auth migrations
npx better-auth migrate
```

### Issue: CORS errors

**Solution**: Ensure backend CORS configuration allows frontend origin:
```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue: Session not persisting

**Solution**: Check cookie settings in Better Auth config:
- `httpOnly: true`
- `secure: false` (for localhost)
- `sameSite: "lax"`

---

## Next Steps

1. **Implement Login Page**: Create login form with Better Auth
2. **Implement Dashboard**: Create dashboard with stats cards
3. **Implement Invoice Form**: Create invoice creation form with React Hook Form
4. **Implement Invoice Table**: Create invoice list with TanStack Table
5. **Add Validation**: Implement Zod schemas for forms
6. **Add Error Handling**: Create error boundaries and toast notifications
7. **Add Loading States**: Create skeleton screens
8. **Test Workflows**: Test complete invoice lifecycle

---

## Development Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linter
npm run lint

# Run type check
npx tsc --noEmit

# Add shadcn/ui component
npx shadcn@latest add <component-name>
```

---

## Useful Resources

- **Next.js Docs**: https://nextjs.org/docs
- **shadcn/ui**: https://ui.shadcn.com
- **React Query**: https://tanstack.com/query/latest
- **React Hook Form**: https://react-hook-form.com
- **Better Auth**: https://www.better-auth.com
- **Tailwind CSS**: https://tailwindcss.com

---

## Support

For issues or questions:
1. Check backend API is running
2. Verify environment variables
3. Check browser console for errors
4. Review API contracts documentation
5. Consult team documentation

---

**Setup Complete!** You're ready to start building the FBR Invoice Portal frontend.
