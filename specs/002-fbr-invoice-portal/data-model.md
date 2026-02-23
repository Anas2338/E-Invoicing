# Data Model: FBR Invoice Integration Portal Frontend

**Feature**: 002-fbr-invoice-portal
**Date**: 2026-02-23
**Purpose**: Define frontend data structures and their relationships

## Overview

This document defines the TypeScript interfaces and types used in the frontend application. These models represent data structures for UI state, API communication, and form handling.

**Note**: The frontend does NOT own the database schema. These models are TypeScript representations of data received from or sent to the backend API.

---

## Core Entities

### User

Represents an authenticated business taxpayer.

```typescript
interface User {
  id: string
  email: string
  businessName: string
  taxId: string
  productionApproved: boolean
  createdAt: string // ISO 8601
  updatedAt: string // ISO 8601
}
```

**Attributes**:
- `id`: Unique user identifier (UUID from backend)
- `email`: User's email address
- `businessName`: Registered business name
- `taxId`: Business tax identification number (13 digits)
- `productionApproved`: Flag indicating if user can access production environment
- `createdAt`: Account creation timestamp
- `updatedAt`: Last update timestamp

**Relationships**:
- One user has many invoices
- One user has one session

**Validation Rules**:
- Email must be valid format
- Tax ID must be 13 digits
- Business name required (min 1 character)

---

### Invoice

Represents a sale or purchase invoice in any state of the lifecycle.

```typescript
type InvoiceType = "sale" | "purchase"
type InvoiceStatus = "draft" | "validated" | "posted" | "failed"
type Environment = "sandbox" | "production"

interface Invoice {
  id: string
  userId: string
  invoiceNumber: string
  type: InvoiceType
  status: InvoiceStatus
  environment: Environment

  // Invoice header
  invoiceDate: string // ISO 8601 date
  dueDate?: string // ISO 8601 date (optional)

  // Customer/Supplier details
  customerName: string
  customerTaxId: string
  customerAddress?: string

  // Line items
  lineItems: LineItem[]

  // Calculated totals
  subtotal: number // Sum of all line item amounts before tax
  taxTotal: number // Sum of all tax amounts
  grandTotal: number // Subtotal + taxTotal

  // FBR integration
  fbrReference?: string // FBR validation/posting reference
  fbrResponse?: FBRResponse // Full FBR response data

  // Metadata
  createdAt: string // ISO 8601
  updatedAt: string // ISO 8601
  validatedAt?: string // ISO 8601
  postedAt?: string // ISO 8601
}
```

**Attributes**:
- `id`: Unique invoice identifier (UUID)
- `userId`: Owner of the invoice
- `invoiceNumber`: Business invoice number (format: INV-XXXXXX)
- `type`: Sale or purchase invoice
- `status`: Current state in lifecycle
- `environment`: Sandbox or production
- `invoiceDate`: Date invoice was issued
- `dueDate`: Payment due date (optional)
- `customerName`: Customer/supplier name
- `customerTaxId`: Customer/supplier tax ID
- `customerAddress`: Customer/supplier address (optional)
- `lineItems`: Array of invoice line items
- `subtotal`: Total before tax
- `taxTotal`: Total tax amount
- `grandTotal`: Final amount
- `fbrReference`: FBR validation/posting reference number
- `fbrResponse`: Complete FBR API response
- `createdAt`: Invoice creation timestamp
- `updatedAt`: Last modification timestamp
- `validatedAt`: FBR validation timestamp
- `postedAt`: FBR posting timestamp

**Relationships**:
- One invoice belongs to one user
- One invoice has many line items
- One invoice has one FBR response (optional)

**State Transitions**:
```
draft → validated → posted
  ↓         ↓
failed ← failed
```

**Validation Rules**:
- Invoice number must match format: `^INV-\d{6}$`
- Customer name required (min 1 character)
- Customer tax ID must be 13 digits
- Must have at least 1 line item
- Maximum 100 line items
- Due date must be >= invoice date
- Subtotal = sum of all line item amounts
- Tax total = sum of all line item taxes
- Grand total = subtotal + tax total

---

### LineItem

Represents a single item or service on an invoice.

```typescript
interface LineItem {
  id: string // Client-generated UUID for form handling
  description: string
  quantity: number
  unitPrice: number
  taxRate: number // Percentage (0-100)
  taxAmount: number // Calculated: (quantity * unitPrice) * (taxRate / 100)
  amount: number // Calculated: (quantity * unitPrice) + taxAmount
}
```

**Attributes**:
- `id`: Unique identifier (client-generated for form array handling)
- `description`: Item/service description
- `quantity`: Number of units
- `unitPrice`: Price per unit (PKR)
- `taxRate`: Tax percentage (0-100)
- `taxAmount`: Calculated tax amount
- `amount`: Total line amount including tax

**Relationships**:
- One line item belongs to one invoice

**Validation Rules**:
- Description required (min 1 character)
- Quantity must be positive number
- Unit price must be positive number
- Tax rate must be 0-100
- Tax amount = (quantity × unitPrice) × (taxRate / 100)
- Amount = (quantity × unitPrice) + taxAmount

**Calculations**:
```typescript
const subtotal = quantity * unitPrice
const taxAmount = subtotal * (taxRate / 100)
const amount = subtotal + taxAmount
```

---

### Session

Represents user authentication session.

```typescript
interface Session {
  user: User
  token: string // JWT token (stored in HTTP-only cookie)
  expiresAt: string // ISO 8601
}
```

**Attributes**:
- `user`: Authenticated user data
- `token`: JWT authentication token
- `expiresAt`: Session expiration timestamp

**Relationships**:
- One session belongs to one user

**Security**:
- Token stored in HTTP-only cookie (not accessible via JavaScript)
- Secure flag enabled for HTTPS
- SameSite=lax for CSRF protection

---

### FBRResponse

Represents the complete response from FBR API.

```typescript
interface FBRResponse {
  success: boolean
  reference?: string // FBR reference number
  timestamp: string // ISO 8601
  errors?: FBRError[]
  rawResponse: Record<string, any> // Complete FBR response
}

interface FBRError {
  code: string
  message: string
  field?: string
}
```

**Attributes**:
- `success`: Whether FBR operation succeeded
- `reference`: FBR reference number (if successful)
- `timestamp`: Response timestamp
- `errors`: Array of FBR error messages
- `rawResponse`: Unmodified FBR API response

**Usage**:
- Stored with invoice for audit trail
- Displayed to user for debugging
- Used for error mapping to user-friendly messages

---

## Form Models

### InvoiceFormData

Form-specific model with validation schema.

```typescript
import { z } from "zod"

export const lineItemSchema = z.object({
  id: z.string().uuid(),
  description: z.string().min(1, "Description required"),
  quantity: z.number().positive("Quantity must be positive"),
  unitPrice: z.number().positive("Unit price must be positive"),
  taxRate: z.number().min(0).max(100, "Tax rate must be 0-100"),
  taxAmount: z.number(),
  amount: z.number()
})

export const invoiceFormSchema = z.object({
  invoiceNumber: z.string().regex(/^INV-\d{6}$/, "Format: INV-XXXXXX"),
  type: z.enum(["sale", "purchase"]),
  environment: z.enum(["sandbox", "production"]),
  invoiceDate: z.date(),
  dueDate: z.date().optional(),
  customerName: z.string().min(1, "Customer name required"),
  customerTaxId: z.string().regex(/^\d{13}$/, "Tax ID must be 13 digits"),
  customerAddress: z.string().optional(),
  lineItems: z.array(lineItemSchema)
    .min(1, "At least one line item required")
    .max(100, "Maximum 100 line items allowed"),
  subtotal: z.number(),
  taxTotal: z.number(),
  grandTotal: z.number()
}).refine((data) => {
  if (data.dueDate) {
    return data.dueDate >= data.invoiceDate
  }
  return true
}, {
  message: "Due date must be on or after invoice date",
  path: ["dueDate"]
})

export type InvoiceFormData = z.infer<typeof invoiceFormSchema>
```

**Default Values**:
```typescript
const defaultLineItem: LineItem = {
  id: crypto.randomUUID(),
  description: "",
  quantity: 1,
  unitPrice: 0,
  taxRate: 0,
  taxAmount: 0,
  amount: 0
}

const defaultInvoiceForm: Partial<InvoiceFormData> = {
  type: "sale",
  environment: "sandbox",
  invoiceDate: new Date(),
  lineItems: [defaultLineItem]
}
```

---

## API Request/Response Models

### Create Invoice Request

```typescript
interface CreateInvoiceRequest {
  invoiceNumber: string
  type: InvoiceType
  environment: Environment
  invoiceDate: string // ISO 8601
  dueDate?: string // ISO 8601
  customerName: string
  customerTaxId: string
  customerAddress?: string
  lineItems: Omit<LineItem, "id">[] // Backend generates IDs
}
```

### Create Invoice Response

```typescript
interface CreateInvoiceResponse {
  invoice: Invoice
  message: string
}
```

### Validate Invoice Request

```typescript
interface ValidateInvoiceRequest {
  invoiceId: string
}
```

### Validate Invoice Response

```typescript
interface ValidateInvoiceResponse {
  success: boolean
  invoice: Invoice
  fbrResponse: FBRResponse
}
```

### Post Invoice Request

```typescript
interface PostInvoiceRequest {
  invoiceIds: string[] // Support bulk posting
}
```

### Post Invoice Response

```typescript
interface PostInvoiceResponse {
  results: Array<{
    invoiceId: string
    success: boolean
    invoice?: Invoice
    error?: string
  }>
}
```

### List Invoices Request

```typescript
interface ListInvoicesRequest {
  status?: InvoiceStatus[]
  type?: InvoiceType[]
  environment?: Environment[]
  dateFrom?: string // ISO 8601
  dateTo?: string // ISO 8601
  page?: number
  pageSize?: number
}
```

### List Invoices Response

```typescript
interface ListInvoicesResponse {
  invoices: Invoice[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}
```

### Dashboard Stats Response

```typescript
interface DashboardStats {
  draftCount: number
  validatedCount: number
  postedCount: number
  failedCount: number
  recentInvoices: Invoice[] // Last 10
}
```

---

## UI State Models

### Filter State

```typescript
interface InvoiceFilters {
  status: InvoiceStatus[]
  type: InvoiceType[]
  environment: Environment[]
  dateRange: {
    from?: Date
    to?: Date
  }
  searchQuery?: string
}
```

### Table State

```typescript
interface TableState {
  sorting: {
    column: string
    direction: "asc" | "desc"
  }[]
  pagination: {
    pageIndex: number
    pageSize: number
  }
  rowSelection: Record<string, boolean> // { [invoiceId]: selected }
}
```

### Modal State

```typescript
interface ModalState {
  isOpen: boolean
  mode: "view" | "edit" | "delete"
  invoiceId?: string
}
```

---

## Error Models

### API Error

```typescript
interface APIError {
  message: string
  code: string
  status: number
  details?: Record<string, any>
  timestamp: string
}
```

### Form Error

```typescript
interface FormError {
  field: string
  message: string
}
```

---

## Type Guards

```typescript
export function isInvoiceDraft(invoice: Invoice): boolean {
  return invoice.status === "draft"
}

export function isInvoiceValidated(invoice: Invoice): boolean {
  return invoice.status === "validated"
}

export function isInvoicePosted(invoice: Invoice): boolean {
  return invoice.status === "posted"
}

export function canPostInvoice(invoice: Invoice): boolean {
  return invoice.status === "validated"
}

export function canEditInvoice(invoice: Invoice): boolean {
  return invoice.status === "draft" || invoice.status === "failed"
}

export function canDeleteInvoice(invoice: Invoice): boolean {
  return invoice.status === "draft"
}
```

---

## Utility Types

```typescript
// Omit sensitive fields for display
export type PublicUser = Omit<User, "taxId">

// Partial invoice for list views
export type InvoiceListItem = Pick<
  Invoice,
  "id" | "invoiceNumber" | "type" | "status" | "environment" |
  "customerName" | "grandTotal" | "createdAt"
>

// Invoice summary for dashboard
export type InvoiceSummary = Pick<
  Invoice,
  "id" | "invoiceNumber" | "status" | "grandTotal" | "createdAt"
>
```

---

## Constants

```typescript
export const INVOICE_STATUS_LABELS: Record<InvoiceStatus, string> = {
  draft: "Draft",
  validated: "Validated",
  posted: "Posted",
  failed: "Failed"
}

export const INVOICE_TYPE_LABELS: Record<InvoiceType, string> = {
  sale: "Sale Invoice",
  purchase: "Purchase Invoice"
}

export const ENVIRONMENT_LABELS: Record<Environment, string> = {
  sandbox: "Sandbox",
  production: "Production"
}

export const MAX_LINE_ITEMS = 100
export const MIN_LINE_ITEMS = 1
export const TAX_ID_LENGTH = 13
export const INVOICE_NUMBER_PATTERN = /^INV-\d{6}$/
```

---

## Notes

1. All monetary values are in PKR (Pakistani Rupee)
2. All dates are ISO 8601 strings for API communication
3. All IDs are UUIDs
4. Line item IDs are client-generated for form handling (not persisted)
5. Backend is the source of truth for all data
6. Frontend models are TypeScript representations only
7. Zod schemas provide runtime validation
8. Type guards provide type-safe state checks
