# Data Model: Invoice PDF Printing

**Feature**: 001-invoice-pdf-printing  
**Date**: 2026-04-14  

## Overview

This feature does not introduce new database models. It operates on existing `AutomationInvoice` data to generate PDF documents on-demand.

## Existing Models Used

### AutomationInvoice (Read-Only)

**Table**: `automation_invoice`  
**Purpose**: Source of invoice data for PDF generation

**Fields Used**:
- `id` (UUID): Primary key for invoice identification
- `user_id` (UUID): Owner of the invoice (for authorization)
- `invoice_number` (str): Displayed in PDF header and filename
- `invoice_data` (JSON): Complete invoice payload including:
  - Invoice header: seller/buyer details, dates, registration types
  - Line items: products, quantities, rates, taxes
  - Totals: subtotal, taxes, grand total
- `fbr_response` (JSON): Contains USIN for QR code generation
- `status` (enum): Must be "submitted" for PDF generation
- `scheduled_date` (date): Used in PDF filename
- `created_at` (datetime): Audit trail

**Relationships**:
- `user`: Many-to-one with User model (for authorization)

**Access Pattern**:
```python
# Single invoice
invoice = session.exec(
    select(AutomationInvoice)
    .where(AutomationInvoice.id == invoice_id)
    .where(AutomationInvoice.user_id == current_user.id)
).first()

# Batch invoices
invoices = session.exec(
    select(AutomationInvoice)
    .where(AutomationInvoice.id.in_(invoice_ids))
    .where(AutomationInvoice.user_id == current_user.id)
    .where(AutomationInvoice.status == "submitted")
).all()
```

## Data Flow

### Single Invoice PDF Generation

```
┌─────────────┐
│   Frontend  │
│  (User)     │
└──────┬──────┘
       │ GET /api/v1/automation/invoices/{id}/pdf
       │ Headers: Authorization: Bearer {jwt}
       ▼
┌─────────────────────────────────────────────┐
│  Backend API (pdf.py)                       │
│  1. Verify JWT                              │
│  2. Extract user_id from token              │
│  3. Query AutomationInvoice by id + user_id │
│  4. Validate status == "submitted"          │
│  5. Validate fbr_response contains USIN     │
└──────┬──────────────────────────────────────┘
       │ AutomationInvoice object
       ▼
┌─────────────────────────────────────────────┐
│  PDFService (pdf_service.py)                │
│  1. Extract invoice_data (JSON)             │
│  2. Extract USIN from fbr_response          │
│  3. Load FBR logo image                     │
│  4. Generate QR code from USIN              │
│  5. Create PDF canvas (A4)                  │
│  6. Render invoice header                   │
│  7. Render line items table                 │
│  8. Render totals                           │
│  9. Add logo and QR code to footer          │
│  10. Save to BytesIO buffer                 │
└──────┬──────────────────────────────────────┘
       │ PDF bytes
       ▼
┌─────────────────────────────────────────────┐
│  Backend API Response                       │
│  StreamingResponse(                         │
│    buffer,                                  │
│    media_type="application/pdf",            │
│    headers={                                │
│      "Content-Disposition": "attachment;    │
│       filename=Invoice-{num}-{date}.pdf"    │
│    }                                        │
│  )                                          │
└──────┬──────────────────────────────────────┘
       │ HTTP Response (PDF binary)
       ▼
┌─────────────┐
│   Frontend  │
│  Triggers   │
│  Download   │
└─────────────┘
```

### Batch Invoice PDF Generation

```
┌─────────────┐
│   Frontend  │
│  (User)     │
└──────┬──────┘
       │ POST /api/v1/automation/invoices/batch-pdf
       │ Body: { "invoice_ids": ["uuid1", "uuid2", ...] }
       │ Headers: Authorization: Bearer {jwt}
       ▼
┌─────────────────────────────────────────────┐
│  Backend API (pdf.py)                       │
│  1. Verify JWT                              │
│  2. Validate batch size <= 50               │
│  3. Query all invoices by ids + user_id     │
│  4. Validate all status == "submitted"      │
│  5. Validate all have USIN                  │
│  6. Order by selection order (preserve IDs) │
└──────┬──────────────────────────────────────┘
       │ List[AutomationInvoice]
       ▼
┌─────────────────────────────────────────────┐
│  PDFService (pdf_service.py)                │
│  1. Create single PDF canvas                │
│  2. For each invoice:                       │
│     - Render invoice page                   │
│     - Add page break (except last)          │
│  3. Save all pages to buffer                │
└──────┬──────────────────────────────────────┘
       │ PDF bytes (multi-page)
       ▼
┌─────────────────────────────────────────────┐
│  Backend API Response                       │
│  StreamingResponse with batch filename      │
└──────┬──────────────────────────────────────┘
       │ HTTP Response
       ▼
┌─────────────┐
│   Frontend  │
│  Downloads  │
│  Batch PDF  │
└─────────────┘
```

## Data Structures

### Invoice Data JSON Structure (from invoice_data field)

```json
{
  "invoiceType": "Sale Invoice",
  "invoiceDate": "2025-04-21",
  "sellerNTNCNIC": "1234567",
  "sellerBusinessName": "Company ABC",
  "sellerProvince": "Sindh",
  "sellerAddress": "Karachi",
  "buyerNTNCNIC": "7654321",
  "buyerBusinessName": "Buyer XYZ",
  "buyerProvince": "Punjab",
  "buyerAddress": "Lahore",
  "buyerRegistrationType": "Registered",
  "invoiceRefNo": "INV-001",
  "items": [
    {
      "hsCode": "0101.2100",
      "productDescription": "Product Name",
      "rate": "18%",
      "uoM": "Numbers, pieces, units",
      "quantity": 10.0,
      "totalValues": 11800.00,
      "valueSalesExcludingST": 10000.00,
      "fixedNotifiedValueOrRetailPrice": 0.00,
      "salesTaxApplicable": 1800.00,
      "salesTaxWithheldAtSource": 0.00,
      "extraTax": 0.00,
      "furtherTax": 0.00,
      "fedPayable": 0.00,
      "discount": 0.00,
      "saleType": "Goods at standard rate (default)"
    }
  ]
}
```

### FBR Response JSON Structure (from fbr_response field)

```json
{
  "invoiceNumber": "7000007DI1747119701593",
  "dated": "2025-05-13 12:01:41",
  "validationResponse": {
    "statusCode": "00",
    "status": "Valid",
    "error": "",
    "invoiceStatuses": [
      {
        "itemSNo": "1",
        "statusCode": "00",
        "status": "Valid",
        "invoiceNo": "7000007DI1747119701593-1",
        "errorCode": "",
        "error": ""
      }
    ]
  }
}
```

**USIN Extraction**: `fbr_response["invoiceNumber"]` → "7000007DI1747119701593"

## PDF Document Structure

### Page Layout (A4: 210mm x 297mm)

```
┌─────────────────────────────────────────────┐
│  INVOICE                                    │
│  Invoice #: {invoice_number}                │
│  Date: {invoiceDate}                        │
│                                             │
│  SELLER DETAILS                             │
│  Name: {sellerBusinessName}                 │
│  NTN/CNIC: {sellerNTNCNIC}                  │
│  Address: {sellerAddress}, {sellerProvince} │
│                                             │
│  BUYER DETAILS                              │
│  Name: {buyerBusinessName}                  │
│  NTN/CNIC: {buyerNTNCNIC}                   │
│  Address: {buyerAddress}, {buyerProvince}   │
│  Type: {buyerRegistrationType}              │
│                                             │
│  LINE ITEMS                                 │
│  ┌────┬──────┬─────┬────┬──────┬──────┐    │
│  │HS  │Desc  │Qty  │UoM │Rate  │Total │    │
│  ├────┼──────┼─────┼────┼──────┼──────┤    │
│  │... │...   │...  │... │...   │...   │    │
│  └────┴──────┴─────┴────┴──────┴──────┘    │
│                                             │
│  TOTALS                                     │
│  Subtotal (excl. ST): {valueSalesExcludingST}│
│  Sales Tax: {salesTaxApplicable}            │
│  Withholding Tax: {salesTaxWithheldAtSource}│
│  Extra Tax: {extraTax}                      │
│  Further Tax: {furtherTax}                  │
│  FED: {fedPayable}                          │
│  Grand Total: {totalValues}                 │
│                                             │
│  ┌──────────┐  ┌──────────┐                │
│  │ FBR Logo │  │ QR Code  │                │
│  │          │  │ (USIN)   │                │
│  └──────────┘  └──────────┘                │
│  FBR Digital Invoicing System               │
│  USIN: {invoiceNumber}                      │
└─────────────────────────────────────────────┘
```

## Validation Rules

### Pre-Generation Validation

1. **Invoice Existence**: Invoice ID must exist in database
2. **Authorization**: Invoice must belong to current user
3. **Status Check**: Invoice status must be "submitted"
4. **USIN Presence**: `fbr_response["invoiceNumber"]` must exist and be non-empty
5. **Batch Size**: Batch requests must have 1-50 invoice IDs
6. **Batch Ownership**: All invoices in batch must belong to current user
7. **Batch Status**: All invoices in batch must be "submitted"

### Data Validation

1. **Invoice Data**: Must be valid JSON with required fields
2. **Line Items**: Must have at least one item
3. **Numeric Fields**: Must be valid numbers (not null/undefined)
4. **Text Fields**: Must handle Unicode characters (Urdu/Arabic)

## Error Handling

### Error Scenarios

| Scenario | HTTP Status | Error Message |
|----------|-------------|---------------|
| Invoice not found | 404 | "Invoice not found" |
| Not authorized | 403 | "You do not have permission to access this invoice" |
| Invalid status | 400 | "Invoice must be submitted before printing" |
| Missing USIN | 400 | "Invoice does not have a valid FBR submission response" |
| Batch size exceeded | 400 | "Maximum 50 invoices allowed per batch" |
| Empty batch | 400 | "At least one invoice ID required" |
| Logo missing | 500 | "FBR logo file not found" |
| QR generation failed | 500 | "Failed to generate QR code" |
| PDF generation failed | 500 | "Failed to generate PDF" |

## Performance Considerations

### Query Optimization

- Use `select()` with explicit column selection (avoid SELECT *)
- Index on `user_id` and `status` already exists
- Batch query uses `IN` clause (efficient for up to 50 IDs)

### Memory Management

- Single invoice: ~100-500 KB PDF
- Batch (50 invoices): ~5-25 MB PDF
- Peak memory during generation: ~50-100 MB
- No disk I/O required (in-memory generation)

### Caching Strategy

- **No PDF Caching**: Generate on-demand per spec
- **Asset Caching**: Load logo and font once per request
- **QR Code**: Generate fresh for each invoice (fast operation)

## Security Considerations

### Authorization

- Row-level security: `WHERE user_id = current_user.id`
- No cross-user data access possible
- JWT verification via existing middleware

### Data Exposure

- Only user's own invoices accessible
- No sensitive data in QR code (only USIN)
- No user input in PDF content (all from database)

### Input Validation

- UUID format validation for invoice IDs
- Batch size limit enforcement (max 50)
- Status validation before generation

## Logging and Audit

### Log Events

1. **PDF Generation Started**: Log invoice ID(s), user ID, timestamp
2. **PDF Generation Completed**: Log success, generation time, PDF size
3. **PDF Generation Failed**: Log error details, invoice ID, user ID
4. **Validation Failures**: Log reason, invoice ID, user ID

### Log Format

```python
logger.info(f"PDF generation started: user={user_id}, invoice={invoice_id}")
logger.info(f"PDF generated successfully: invoice={invoice_id}, size={len(pdf_bytes)} bytes, time={elapsed}s")
logger.error(f"PDF generation failed: invoice={invoice_id}, error={str(e)}")
```

### Audit Trail

- Use existing `automation_log` table to record PDF generation events
- Action: "generate_pdf" or "generate_batch_pdf"
- Status: "success" or "failure"
- Details: Include invoice IDs, generation time, error messages
