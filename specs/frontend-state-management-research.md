# State Management Strategy Research - FBR Invoice Portal

**Date:** 2026-02-23
**Context:** Frontend architecture for FBR Invoice Portal with Next.js App Router

## Executive Summary

After researching React Query (TanStack Query), SWR, and Next.js native data fetching, the **recommended approach is React Query (TanStack Query)** for the FBR Invoice Portal, with selective use of Next.js Server Components for initial page loads.

## Server State (API Data)

### Recommended: React Query (TanStack Query)

React Query provides the most comprehensive solution for managing server state in complex applications like the invoice portal.

**Key Features:**
- **Sophisticated Caching:** Configurable `staleTime` and cache invalidation strategies
- **Optimistic Updates:** Built-in rollback mechanism for failed mutations
- **TypeScript Support:** Full type safety with generics for queries and mutations
- **Next.js Integration:** Works seamlessly with App Router via `HydrationBoundary`
- **Developer Experience:** Excellent DevTools for debugging cache state

**Implementation Pattern:**

```typescript
// app/providers.tsx
'use client'

import { QueryClient, QueryClientProvider, isServer } from '@tanstack/react-query'

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 60 seconds
        gcTime: 5 * 60 * 1000, // 5 minutes
        retry: 3,
        refetchOnWindowFocus: false,
      },
    },
  })
}

let browserQueryClient: QueryClient | undefined = undefined

function getQueryClient() {
  if (isServer) {
    return makeQueryClient()
  } else {
    if (!browserQueryClient) browserQueryClient = makeQueryClient()
    return browserQueryClient
  }
}

export default function Providers({ children }: { children: React.ReactNode }) {
  const queryClient = getQueryClient()
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}
```

**Query Pattern (Fetching Invoices):**

```typescript
// hooks/useInvoices.ts
import { useQuery } from '@tanstack/react-query'

interface Invoice {
  id: string
  invoiceNumber: string
  amount: number
  status: 'draft' | 'submitted' | 'approved' | 'rejected'
  createdAt: string
}

export function useInvoices(filters?: { status?: string; page?: number }) {
  return useQuery<Invoice[]>({
    queryKey: ['invoices', filters],
    queryFn: async () => {
      const params = new URLSearchParams(filters as any)
      const response = await fetch(`/api/invoices?${params}`)
      if (!response.ok) throw new Error('Failed to fetch invoices')
      return response.json()
    },
    staleTime: 30 * 1000, // 30 seconds for invoice list
  })
}
```

**Mutation Pattern (Create/Update Invoice):**

```typescript
// hooks/useInvoiceMutations.ts
import { useMutation, useQueryClient } from '@tanstack/react-query'

export function useCreateInvoice() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (invoice: Partial<Invoice>) => {
      const response = await fetch('/api/invoices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(invoice),
      })
      if (!response.ok) throw new Error('Failed to create invoice')
      return response.json()
    },
    onMutate: async (newInvoice, context) => {
      // Cancel outgoing refetches
      await context.client.cancelQueries({ queryKey: ['invoices'] })

      // Snapshot previous value
      const previousInvoices = context.client.getQueryData<Invoice[]>(['invoices'])

      // Optimistically update cache
      context.client.setQueryData<Invoice[]>(['invoices'], (old) => [
        ...(old || []),
        { ...newInvoice, id: 'temp-' + Date.now() } as Invoice,
      ])

      return { previousInvoices }
    },
    onError: (err, newInvoice, onMutateResult, context) => {
      // Rollback on error
      context.client.setQueryData(['invoices'], onMutateResult?.previousInvoices)
    },
    onSettled: (data, error, variables, onMutateResult, context) => {
      // Refetch to ensure consistency
      context.client.invalidateQueries({ queryKey: ['invoices'] })
    },
  })
}
```

## UI State (Local State)

### Recommended: React useState + useReducer

For local UI state (form inputs, modals, filters), use React's built-in hooks:

- **Simple state:** `useState` for individual form fields, toggles
- **Complex state:** `useReducer` for multi-step forms, complex filter logic
- **Form management:** Consider React Hook Form for complex invoice forms

**Example:**

```typescript
// components/InvoiceFilters.tsx
'use client'

import { useState } from 'react'

export function InvoiceFilters({ onFilterChange }: { onFilterChange: (filters: any) => void }) {
  const [status, setStatus] = useState<string>('')
  const [dateRange, setDateRange] = useState<{ from: Date; to: Date } | null>(null)

  const handleApplyFilters = () => {
    onFilterChange({ status, dateRange })
  }

  return (
    <div>
      <select value={status} onChange={(e) => setStatus(e.target.value)}>
        <option value="">All Statuses</option>
        <option value="draft">Draft</option>
        <option value="submitted">Submitted</option>
      </select>
      <button onClick={handleApplyFilters}>Apply Filters</button>
    </div>
  )
}
```

## Caching Strategy

### Configuration for Invoice Portal

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Cache configuration
      staleTime: 60 * 1000, // Data fresh for 60 seconds
      gcTime: 5 * 60 * 1000, // Keep unused data for 5 minutes

      // Retry configuration
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),

      // Refetch configuration
      refetchOnWindowFocus: false, // Don't refetch on window focus (can be annoying)
      refetchOnReconnect: true, // Refetch when network reconnects
      refetchOnMount: true, // Refetch when component mounts
    },
    mutations: {
      retry: 1, // Retry mutations once
    },
  },
})
```

### Cache Invalidation Patterns

```typescript
// After successful mutation
queryClient.invalidateQueries({ queryKey: ['invoices'] })

// Invalidate specific invoice
queryClient.invalidateQueries({ queryKey: ['invoice', invoiceId] })

// Invalidate all invoice-related queries
queryClient.invalidateQueries({ queryKey: ['invoices'], exact: false })

// Manual refetch
queryClient.refetchQueries({ queryKey: ['invoices'] })
```

## Mutation Patterns

### Create Invoice with Optimistic Update

```typescript
const createMutation = useMutation({
  mutationFn: createInvoice,
  onMutate: async (newInvoice, context) => {
    await context.client.cancelQueries({ queryKey: ['invoices'] })
    const previous = context.client.getQueryData(['invoices'])

    context.client.setQueryData(['invoices'], (old: Invoice[]) => [
      ...old,
      { ...newInvoice, id: 'optimistic-' + Date.now(), status: 'draft' }
    ])

    return { previous }
  },
  onError: (err, variables, onMutateResult, context) => {
    context.client.setQueryData(['invoices'], onMutateResult.previous)
    toast.error('Failed to create invoice')
  },
  onSuccess: (data) => {
    toast.success('Invoice created successfully')
  },
  onSettled: (data, error, variables, onMutateResult, context) => {
    context.client.invalidateQueries({ queryKey: ['invoices'] })
  },
})
```

### Update Invoice

```typescript
const updateMutation = useMutation({
  mutationFn: ({ id, data }: { id: string; data: Partial<Invoice> }) =>
    fetch(`/api/invoices/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(res => res.json()),
  onMutate: async ({ id, data }, context) => {
    await context.client.cancelQueries({ queryKey: ['invoice', id] })
    const previous = context.client.getQueryData(['invoice', id])

    context.client.setQueryData(['invoice', id], (old: Invoice) => ({
      ...old,
      ...data,
    }))

    return { previous, id }
  },
  onError: (err, variables, onMutateResult, context) => {
    context.client.setQueryData(['invoice', onMutateResult.id], onMutateResult.previous)
  },
  onSettled: (data, error, { id }, onMutateResult, context) => {
    context.client.invalidateQueries({ queryKey: ['invoice', id] })
    context.client.invalidateQueries({ queryKey: ['invoices'] })
  },
})
```

### Delete Invoice

```typescript
const deleteMutation = useMutation({
  mutationFn: (id: string) =>
    fetch(`/api/invoices/${id}`, { method: 'DELETE' }),
  onMutate: async (id, context) => {
    await context.client.cancelQueries({ queryKey: ['invoices'] })
    const previous = context.client.getQueryData(['invoices'])

    context.client.setQueryData(['invoices'], (old: Invoice[]) =>
      old.filter(invoice => invoice.id !== id)
    )

    return { previous }
  },
  onError: (err, id, onMutateResult, context) => {
    context.client.setQueryData(['invoices'], onMutateResult.previous)
    toast.error('Failed to delete invoice')
  },
  onSuccess: () => {
    toast.success('Invoice deleted successfully')
  },
})
```

## Error Handling

### Global Error Handler

```typescript
// lib/queryClient.ts
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      onError: (error) => {
        if (error instanceof Error) {
          console.error('Query error:', error.message)
          // Log to error tracking service
          logErrorToService(error)
        }
      },
    },
    mutations: {
      onError: (error) => {
        if (error instanceof Error) {
          console.error('Mutation error:', error.message)
          toast.error(error.message)
        }
      },
    },
  },
})
```

### Component-Level Error Handling

```typescript
function InvoiceList() {
  const { data, error, isLoading, isError } = useInvoices()

  if (isError) {
    return (
      <div className="error-state">
        <h3>Failed to load invoices</h3>
        <p>{error.message}</p>
        <button onClick={() => queryClient.invalidateQueries({ queryKey: ['invoices'] })}>
          Retry
        </button>
      </div>
    )
  }

  if (isLoading) {
    return <InvoiceListSkeleton />
  }

  return <InvoiceTable invoices={data} />
}
```

### Error Boundaries for Suspense

```typescript
import { QueryErrorResetBoundary } from '@tanstack/react-query'
import { ErrorBoundary } from 'react-error-boundary'

function InvoicePage() {
  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <ErrorBoundary
          onReset={reset}
          fallbackRender={({ resetErrorBoundary, error }) => (
            <div>
              <p>Error: {error.message}</p>
              <button onClick={resetErrorBoundary}>Try Again</button>
            </div>
          )}
        >
          <Suspense fallback={<LoadingSpinner />}>
            <InvoiceList />
          </Suspense>
        </ErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  )
}
```

## Comparison Table

| Feature | React Query | SWR | Native Next.js |
|---------|-------------|-----|----------------|
| **Learning Curve** | Medium | Low | Low |
| **Bundle Size** | ~13KB | ~5KB | 0KB (built-in) |
| **TypeScript Support** | Excellent (full generics) | Good | Excellent |
| **Caching Strategy** | Sophisticated (staleTime, gcTime) | Good (dedupingInterval) | Basic (fetch cache) |
| **Optimistic Updates** | Built-in with rollback | Manual with mutate | Not supported |
| **Mutation Handling** | useMutation hook | useSWRMutation | Server Actions |
| **Error Retry** | Configurable with backoff | Configurable | Manual |
| **DevTools** | Excellent | Basic | None |
| **Prefetching** | HydrationBoundary | Manual | Server Components |
| **Request Deduplication** | Yes | Yes | Yes (fetch) |
| **Polling/Intervals** | Built-in | Built-in | Manual |
| **Suspense Support** | useSuspenseQuery | Yes | Native |
| **Next.js App Router** | Good (client components) | Good (client components) | Excellent (native) |
| **Offline Support** | Via plugins | Limited | None |
| **Pagination** | Built-in helpers | Manual | Manual |
| **Infinite Scroll** | useInfiniteQuery | Manual | Manual |
| **Parallel Queries** | useQueries | Multiple useSWR | Multiple fetches |
| **Dependent Queries** | enabled option | Conditional keys | Sequential awaits |
| **Cache Persistence** | Via plugins | Via plugins | None |
| **Community & Ecosystem** | Large | Medium | N/A |
| **Maintenance** | Active (TanStack) | Active (Vercel) | Active (Vercel) |

## Performance Comparison

### Initial Load Performance
- **Next.js Native:** Best (Server Components, no client JS)
- **React Query:** Good (with prefetching)
- **SWR:** Good (with prefetching)

### Subsequent Navigation
- **React Query:** Excellent (sophisticated caching)
- **SWR:** Good (simple caching)
- **Next.js Native:** Varies (depends on cache config)

### Mutation Performance
- **React Query:** Excellent (optimistic updates, rollback)
- **SWR:** Good (optimistic updates)
- **Next.js Native:** Good (Server Actions)

### Perceived Performance (< 1s requirement)
- **React Query:** ✅ Meets requirement (optimistic updates, instant feedback)
- **SWR:** ✅ Meets requirement (optimistic updates)
- **Next.js Native:** ⚠️ May not meet for interactive operations

## Recommendation

### Primary Choice: React Query (TanStack Query)

**Rationale:**

1. **Complex Invoice Workflows:** React Query excels at managing complex CRUD operations with built-in optimistic updates and rollback mechanisms.

2. **Performance Requirements:** Optimistic updates provide instant feedback, easily meeting the < 1s perceived delay requirement.

3. **TypeScript Support:** Full type safety with generics ensures type-safe API calls and responses.

4. **Developer Experience:** Excellent DevTools for debugging, comprehensive documentation, and large community.

5. **Scalability:** As the invoice portal grows, React Query's features (infinite queries, parallel queries, dependent queries) will be valuable.

6. **Error Handling:** Sophisticated error handling with retry logic and error boundaries.

7. **Next.js Integration:** Works seamlessly with App Router via client components and HydrationBoundary for SSR.

### Hybrid Approach (Recommended)

Use **React Query for client-side interactions** and **Next.js Server Components for initial page loads**:

```typescript
// app/invoices/page.tsx (Server Component)
import { dehydrate, HydrationBoundary, QueryClient } from '@tanstack/react-query'
import InvoiceList from './InvoiceList'

export default async function InvoicesPage() {
  const queryClient = new QueryClient()

  // Prefetch on server
  await queryClient.prefetchQuery({
    queryKey: ['invoices'],
    queryFn: getInvoices,
  })

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <InvoiceList />
    </HydrationBoundary>
  )
}
```

```typescript
// app/invoices/InvoiceList.tsx (Client Component)
'use client'

import { useInvoices } from '@/hooks/useInvoices'

export default function InvoiceList() {
  const { data, isLoading } = useInvoices()
  // Client-side interactivity with React Query
}
```

### When to Use Each Approach

**React Query:**
- Invoice list with filters and pagination
- Create/update/delete invoices
- Real-time status updates
- Any interactive data operations

**Next.js Server Components:**
- Initial page load (prefetch with React Query)
- Static content (dashboard stats, reports)
- SEO-critical pages

**Native useState/useReducer:**
- Form inputs
- Modal state
- UI toggles
- Local filters (before applying)

## Implementation Checklist

- [ ] Install dependencies: `@tanstack/react-query @tanstack/react-query-devtools`
- [ ] Set up QueryClientProvider in app layout
- [ ] Configure default query options (staleTime, retry, etc.)
- [ ] Create custom hooks for invoice queries (useInvoices, useInvoice)
- [ ] Create custom hooks for invoice mutations (useCreateInvoice, useUpdateInvoice, useDeleteInvoice)
- [ ] Implement optimistic updates for all mutations
- [ ] Set up error boundaries with QueryErrorResetBoundary
- [ ] Configure error handling and retry logic
- [ ] Add React Query DevTools for development
- [ ] Implement prefetching for initial page loads
- [ ] Set up cache invalidation patterns
- [ ] Add loading states and skeletons
- [ ] Implement toast notifications for mutations
- [ ] Test optimistic updates and rollback scenarios
- [ ] Monitor performance and adjust cache configuration

## References

### Official Documentation
- [TanStack Query Documentation](https://tanstack.com/query/latest)
- [TanStack Query with Next.js App Router](https://tanstack.com/query/latest/docs/framework/react/guides/advanced-ssr)
- [Next.js Data Fetching](https://nextjs.org/docs/app/building-your-application/data-fetching)
- [SWR Documentation](https://swr.vercel.app/)

### Key Concepts
- [Optimistic Updates](https://tanstack.com/query/latest/docs/framework/react/guides/optimistic-updates)
- [Mutations](https://tanstack.com/query/latest/docs/framework/react/guides/mutations)
- [Caching](https://tanstack.com/query/latest/docs/framework/react/guides/caching)
- [Error Handling](https://tanstack.com/query/latest/docs/framework/react/guides/query-retries)

### Community Resources
- [TanStack Query GitHub](https://github.com/tanstack/query)
- [React Query Examples](https://tanstack.com/query/latest/docs/framework/react/examples/react/basic)
