# Research Findings: FBR Invoice Integration Portal Frontend

**Date**: 2026-02-23
**Feature**: 002-fbr-invoice-portal
**Purpose**: Document technology decisions and architectural patterns for frontend implementation

## Executive Summary

This document consolidates research findings from Context7 documentation and best practices analysis for building the FBR Invoice Portal frontend with Next.js 16+ App Router, Tailwind CSS 4.1, TypeScript, and modern React patterns.

## Technology Stack Decisions

### 1. UI Component Library

**Decision**: shadcn/ui + Tailwind CSS 4.1

**Rationale**:
- Zero lock-in: Components are copied into codebase, fully customizable
- Minimal bundle size: ~70% smaller than Material-UI (~15KB base vs ~100KB)
- Excellent table support: Seamless integration with TanStack Table for complex data grids
- Accessibility-first: Built on Radix UI primitives (WCAG 2.1 AA compliant)
- TypeScript native: Full type safety out of the box
- Next.js 16+ App Router optimized: Perfect Server Component support
- No runtime overhead: Tailwind CSS 4.1 generates CSS at build time with improved performance
- Tailwind CSS 4.1 features: Enhanced performance, better CSS-in-JS support, improved configuration

**Alternatives Considered**:
- Material-UI: Comprehensive but large bundle size (~100KB+), CSS-in-JS runtime overhead
- Chakra UI: Good middle ground but still has runtime overhead (~80KB)
- Custom components: Too time-consuming for MVP, reinventing the wheel

**Implementation**:
```bash
npx shadcn@latest init
npx shadcn@latest add table form input button toast dialog
```

**Bundle Size Impact**:
- Base: ~15KB
- With tables: ~45KB
- With forms: ~35KB
- Total estimated: ~60-70KB (vs 180KB+ for MUI)

---

### 2. State Management

**Decision**: React Query (TanStack Query) + Native React Hooks

**Rationale**:
- Built-in optimistic updates with automatic rollback (meets < 1s perceived delay requirement)
- Sophisticated caching for complex invoice workflows
- Excellent TypeScript support with full generics
- Superior developer experience with DevTools
- Scalable for future features (infinite queries, pagination, parallel queries)
- Automatic background refetching and stale-while-revalidate patterns

**Alternatives Considered**:
- SWR: Good but less feature-rich, lacks optimistic updates out of the box
- Native Next.js data fetching: Great for Server Components but insufficient for client-side mutations
- Redux/Zustand: Overkill for this use case, adds unnecessary complexity

**Architecture**:
- **Server state** (API data): React Query
- **UI state** (form inputs, modals, filters): useState/useReducer
- **Server Components**: Native Next.js data fetching with prefetching

**Caching Strategy**:
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})
```

---

### 3. Form Handling

**Decision**: React Hook Form + Zod

**Rationale**:
- Uncontrolled components minimize re-renders (critical for 100+ line items)
- Performance: ~9KB bundle vs Formik's ~15KB
- TypeScript-first: Excellent type inference with Zod
- useFieldArray: Purpose-built for dynamic invoice line items
- Selective re-rendering: useWatch hook for auto-calculations
- Zod provides automatic type inference from schemas

**Alternatives Considered**:
- Formik: Uses controlled components, performance issues with large forms
- Yup: JavaScript-first, requires manual TypeScript typing

**Dynamic Fields Pattern**:
```typescript
const { fields, append, remove } = useFieldArray({
  control,
  name: "lineItems",
  rules: { minLength: 1, maxLength: 100 }
})
```

**Validation Strategy**:
- **Client-side**: Format validation, required fields, ranges (React Hook Form + Zod)
- **Server-side**: Business rules, database constraints, authorization (Backend API)

**Performance Optimization**:
- Virtual scrolling for 100+ line items (react-virtual)
- Selective re-rendering with useWatch
- Memoization for calculated fields
- Debounced validation (onBlur mode)

---

### 4. Authentication

**Decision**: Better Auth with HTTP-only cookies

**Rationale**:
- Native Next.js App Router support
- HTTP-only cookies prevent XSS attacks
- Built-in CSRF protection
- Session persistence across page refreshes
- TypeScript-first API
- Seamless integration with FastAPI backend

**Security Configuration**:
```typescript
export const auth = betterAuth({
  advanced: {
    useSecureCookies: true,
    defaultCookieAttributes: {
      httpOnly: true,
      secure: true,
      sameSite: "lax"
    }
  }
})
```

**Route Protection Strategy**:
- Middleware for optimistic redirects (cookie-based check)
- Server-side session validation in protected pages (actual security)
- Client-side session hooks for UI state

**Session Management**:
- Expiration: 7 days (configurable)
- Update age: 24 hours (sliding window)
- Automatic refresh on activity

---

### 5. Next.js App Router Architecture

**Decision**: Next.js 16+ App Router with route groups and Server Components by default

**Folder Structure**:
```
app/
├── (auth)/              # Route group - login, signup
├── (dashboard)/         # Route group - protected routes
│   ├── dashboard/
│   ├── invoices/
│   └── settings/
├── _components/         # Private folder - not routable
│   ├── server/          # Server Components
│   └── client/          # Client Components
└── _lib/                # Utilities
```

**Server vs Client Components**:
- **Server Components** (default): Layouts, static content, data fetching
- **Client Components** (`'use client'`): Forms, interactive elements, state management

**Performance Targets**:
- Initial page load: < 3 seconds on 3G
- Time to Interactive: < 5 seconds
- Lighthouse score: > 80

**Data Fetching Patterns**:
- Server Components: Native fetch with cache options
- Client Components: React Query for mutations and real-time data
- Parallel fetching: Promise.all() for independent requests
- Streaming: Suspense boundaries for progressive rendering

---

## API Integration Layer

### Central API Client

**Pattern**: Proxy through Next.js API routes to FastAPI backend

**Rationale**:
- Keeps backend URL hidden from client
- Allows session token forwarding
- Enables request/response transformation
- Provides centralized error handling

**Implementation**:
```typescript
// lib/api-client.ts
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`/api/proxy${endpoint}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new APIError(error.message, response.status, error)
  }

  return response.json()
}
```

**Error Normalization**:
```typescript
interface APIError {
  message: string
  code: string
  status: number
  details?: Record<string, any>
}
```

---

## Component Architecture

### Layout Hierarchy

```
RootLayout (app/layout.tsx)
├── Providers (QueryClient, Theme)
├── AuthLayout (app/(auth)/layout.tsx)
│   └── Auth pages (login, signup)
└── DashboardLayout (app/(dashboard)/layout.tsx)
    ├── Sidebar
    ├── Header (with environment selector)
    └── Protected pages
```

### Component Organization

```
components/
├── ui/                  # shadcn/ui base components
│   ├── button.tsx
│   ├── input.tsx
│   ├── table.tsx
│   ├── form.tsx
│   └── toast.tsx
├── features/            # Feature-specific compositions
│   ├── invoices/
│   │   ├── InvoiceTable.tsx
│   │   ├── InvoiceForm.tsx
│   │   ├── LineItemsArray.tsx
│   │   └── InvoiceFilters.tsx
│   ├── auth/
│   │   ├── LoginForm.tsx
│   │   └── SignupForm.tsx
│   └── dashboard/
│       ├── StatsCards.tsx
│       └── RecentInvoices.tsx
└── shared/              # Shared utilities
    ├── ErrorBoundary.tsx
    ├── LoadingSkeleton.tsx
    └── EnvironmentSelector.tsx
```

---

## Form Architecture

### Schema-Driven Forms

**Invoice Schema** (shared with backend):
```typescript
import { z } from "zod"

export const lineItemSchema = z.object({
  description: z.string().min(1, "Description required"),
  quantity: z.number().positive("Must be positive"),
  unitPrice: z.number().positive("Must be positive"),
  taxRate: z.number().min(0).max(100),
  amount: z.number()
})

export const invoiceSchema = z.object({
  invoiceNumber: z.string().regex(/^INV-\d{6}$/, "Invalid format"),
  invoiceDate: z.date(),
  customerName: z.string().min(1, "Customer required"),
  customerTaxId: z.string().regex(/^\d{13}$/, "Invalid tax ID"),
  lineItems: z.array(lineItemSchema)
    .min(1, "At least one line item required")
    .max(100, "Maximum 100 line items"),
  subtotal: z.number(),
  taxTotal: z.number(),
  grandTotal: z.number(),
  environment: z.enum(["sandbox", "production"])
})

export type InvoiceFormData = z.infer<typeof invoiceSchema>
```

### Dynamic Field Rendering

**Line Items with Auto-calculation**:
```typescript
function LineItemsArray({ control, register }) {
  const { fields, append, remove } = useFieldArray({
    control,
    name: "lineItems"
  })

  return (
    <>
      {fields.map((field, index) => (
        <div key={field.id}>
          <Input {...register(`lineItems.${index}.description`)} />
          <Input {...register(`lineItems.${index}.quantity`, { valueAsNumber: true })} />
          <Input {...register(`lineItems.${index}.unitPrice`, { valueAsNumber: true })} />
          <LineItemTotal control={control} index={index} />
          <Button onClick={() => remove(index)}>Remove</Button>
        </div>
      ))}
      <Button onClick={() => append(defaultLineItem)}>Add Item</Button>
    </>
  )
}
```

---

## UI Structure

### Dashboard Layout

**Components**:
- Summary cards (draft, validated, posted, failed counts)
- Recent invoices table (last 10)
- Quick actions (Create Sale/Purchase Invoice)
- Environment selector (Sandbox/Production)

**Data Fetching**:
- Server Component for initial load
- React Query for real-time updates

### Invoice Form Layout

**Sections**:
1. Invoice header (number, date, customer)
2. Line items (dynamic array with add/remove)
3. Totals (auto-calculated)
4. Actions (Save Draft, Validate, Cancel)

**Validation**:
- Real-time field validation on blur
- Form-level validation on submit
- Backend validation on "Validate" action

### Validated Invoices Table

**Features**:
- TanStack Table with sorting, filtering, pagination
- Multi-select with checkboxes
- Bulk actions (Post Selected)
- Status indicators (color-coded badges)

**Implementation**:
```typescript
const table = useReactTable({
  data: invoices,
  columns,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
  getPaginationRowModel: getPaginationRowModel(),
  enableRowSelection: true,
})
```

### Invoice History Table

**Filters**:
- Status (draft, validated, posted, failed)
- Type (sale, purchase)
- Date range (from/to)
- Environment (sandbox, production)

**Actions**:
- View details (modal or page)
- Download PDF
- Re-validate (for failed invoices)

---

## Performance Optimization Strategies

### 1. Code Splitting
- Route-based splitting (automatic with App Router)
- Component-level lazy loading for heavy components
- Dynamic imports for modals and dialogs

### 2. Bundle Optimization
- Tailwind CSS purging (automatic)
- Tree-shaking unused components
- Image optimization with next/image

### 3. Rendering Optimization
- Server Components for static content
- Suspense boundaries for progressive rendering
- Virtual scrolling for large lists (100+ items)
- Memoization for expensive calculations

### 4. Caching Strategy
- React Query for API responses (5-minute stale time)
- Next.js static generation for public pages
- Revalidation for semi-static data (dashboard stats)

### 5. Loading States
- Skeleton screens for better perceived performance
- Optimistic updates for mutations
- Progressive enhancement (works without JS)

---

## Accessibility Considerations

### WCAG 2.1 AA Compliance

**Keyboard Navigation**:
- All interactive elements accessible via keyboard
- Logical tab order
- Focus indicators visible
- Skip links for main content

**Screen Reader Support**:
- Semantic HTML (table, form, button elements)
- ARIA labels for dynamic content
- ARIA live regions for status updates
- Form field associations (label + input)

**Visual Accessibility**:
- Color contrast ratios meet AA standards
- Text resizable up to 200%
- No information conveyed by color alone
- Focus indicators clearly visible

**Form Accessibility**:
```tsx
<Field data-invalid={!!errors?.email}>
  <FieldLabel htmlFor="email">Email</FieldLabel>
  <Input
    id="email"
    aria-invalid={!!errors?.email}
    aria-describedby="email-error"
  />
  {errors?.email && (
    <FieldError id="email-error">{errors.email}</FieldError>
  )}
</Field>
```

---

## Testing Strategy

### Unit Tests
- Utility functions (calculations, formatters)
- Form validation schemas
- API client functions

### Integration Tests
- Form submission flows
- API integration (mocked backend)
- Authentication flows

### E2E Tests (Optional for MVP)
- Complete invoice lifecycle
- Multi-user scenarios
- Error handling

---

## Development Workflow

### Setup Steps
1. Initialize Next.js project with TypeScript
2. Install dependencies (shadcn/ui, React Query, React Hook Form, Zod, Better Auth)
3. Configure Tailwind CSS
4. Set up Better Auth
5. Create folder structure
6. Implement base components
7. Build feature components
8. Integrate with backend API

### Environment Variables
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_BETTER_AUTH_URL=http://localhost:3000
DATABASE_URL=postgresql://...
BETTER_AUTH_SECRET=...
```

---

## References

- **shadcn/ui**: https://ui.shadcn.com/docs
- **Tailwind CSS**: https://tailwindcss.com/docs
- **React Query**: https://tanstack.com/query/latest
- **React Hook Form**: https://react-hook-form.com/
- **Zod**: https://zod.dev/
- **Better Auth**: https://www.better-auth.com
- **Next.js App Router**: https://nextjs.org/docs/app
- **TanStack Table**: https://tanstack.com/table/latest
- **Radix UI**: https://www.radix-ui.com/primitives

---

## Next Steps

1. Proceed to Phase 1: Design & Contracts
2. Create data-model.md with entity definitions
3. Generate API contracts in /contracts/ directory
4. Create quickstart.md for setup instructions
5. Update plan.md with architectural decisions
