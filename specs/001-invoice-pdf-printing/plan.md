# Implementation Plan: Invoice PDF Printing with FBR Compliance

**Branch**: `001-invoice-pdf-printing` | **Date**: 2026-04-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-invoice-pdf-printing/spec.md`

## Summary

Implement on-demand PDF generation for submitted invoices with FBR compliance elements (logo and QR code). Users can print single invoices or batch print up to 50 invoices in selection order. PDFs are generated server-side using ReportLab, include all invoice data in a formatted layout, and contain a QR code encoding the FBR-issued USIN for verification. No PDF storage - all generation is on-demand.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript/Next.js 16+ (frontend)
**Primary Dependencies**: FastAPI, ReportLab (PDF generation), qrcode (QR code generation), Pillow (image handling)
**Storage**: Neon PostgreSQL (existing AutomationInvoice model, no PDF storage)
**Testing**: pytest (backend unit/integration tests), Jest/React Testing Library (frontend)
**Target Platform**: Linux server (backend), Web browsers (frontend)
**Project Type**: Web application (backend + frontend)
**Performance Goals**: Single invoice PDF in <3 seconds, batch of 50 invoices in <150 seconds
**Constraints**: 
- On-demand generation only (no PDF caching/storage)
- 50 invoice maximum per batch request
- QR code must be Version 2.0, 25x25 modules, 1.0x1.0 inch
- A4 page size (210mm x 297mm)
- Must support Unicode (Urdu, Arabic characters)
**Scale/Scope**: 
- Existing automation system with invoice management
- Integration with existing AutomationInvoice model
- 2 new API endpoints, 1 new service, frontend UI updates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Compliance-First Development
✅ **PASS** - PDF layout and QR code specifications derived directly from FBR technical documentation (TECHNICAL.txt lines 1128-1131)

### Security by Design
✅ **PASS** - JWT authentication required for all PDF endpoints, row-level security enforced (user can only print their own invoices)

### Spec-Driven Implementation
✅ **PASS** - Invoice data sourced from existing AutomationInvoice.invoice_data (JSON) and fbr_response fields, no hardcoded assumptions

### Data Integrity and Auditability
✅ **PASS** - PDF generation events will be logged via existing automation_log system, no modification of invoice data

### Environment Isolation
✅ **PASS** - PDF generation uses existing invoice data regardless of environment, no environment-specific logic needed

### Security Standards
✅ **PASS** - JWT verification via existing auth middleware, user_id filtering in queries, input validation for invoice IDs and batch limits

### Architectural Constraints
✅ **PASS** - Backend: FastAPI, Frontend: Next.js App Router, ORM: SQLModel, Database: Neon PostgreSQL, Auth: Better Auth

### Data Rules
✅ **PASS** - No invoice modification, read-only access to invoice_data and fbr_response, logging of PDF generation events

### API Design Rules
✅ **PASS** - RESTful endpoints under /api/v1/automation/invoices/, versioned, schema-based responses

### Non-Functional Standards
✅ **PASS** - Performance targets defined (<3s single, <150s batch), concurrent request handling via FastAPI async

### Development Guidelines
✅ **PASS** - Minimal changes to existing code, new service and endpoints only, no refactoring of unrelated components

**Result**: All constitution checks PASS. No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-invoice-pdf-printing/
├── plan.md              # This file
├── research.md          # Phase 0 output (PDF library evaluation, QR code specs)
├── data-model.md        # Phase 1 output (PDF generation data flow)
├── quickstart.md        # Phase 1 output (developer setup guide)
├── contracts/           # Phase 1 output (API contracts)
│   └── pdf-api.yaml    # OpenAPI spec for PDF endpoints
└── tasks.md             # Phase 2 output (NOT created by /sp.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/v1/automation/
│   │   ├── pdf.py                    # NEW: PDF generation endpoints
│   │   ├── dashboard.py              # EXISTING
│   │   ├── excel.py                  # EXISTING
│   │   └── ...
│   ├── services/
│   │   ├── pdf_service.py            # NEW: PDF generation logic
│   │   ├── automation_service.py     # EXISTING
│   │   └── ...
│   ├── models/
│   │   ├── automation_invoice.py     # EXISTING (no changes)
│   │   └── ...
│   └── assets/
│       └── fbr_logo.png              # NEW: FBR Digital Invoicing logo
└── tests/
    ├── unit/
    │   └── test_pdf_service.py       # NEW: PDF service unit tests
    └── integration/
        └── test_pdf_api.py           # NEW: PDF API integration tests

frontend/
├── src/
│   ├── app/(protected)/automation/
│   │   ├── dashboard/
│   │   │   └── page.tsx              # MODIFY: Add print buttons
│   │   └── ...
│   ├── components/automation/
│   │   ├── InvoiceDetail.tsx         # MODIFY: Add print button
│   │   ├── InvoiceTable.tsx          # MODIFY: Add batch print UI
│   │   └── PrintInvoiceButton.tsx    # NEW: Print button component
│   └── services/
│       └── automationApi.ts          # MODIFY: Add PDF endpoints
└── tests/
    └── components/
        └── PrintInvoiceButton.test.tsx  # NEW: Component tests
```

**Structure Decision**: Web application structure (backend + frontend). PDF generation is backend-only for security and consistency. Frontend provides UI triggers and handles PDF download/display. Integrates with existing automation feature structure under `/api/v1/automation/` and reuses existing authentication, authorization, and data access patterns.

## Complexity Tracking

> No constitution violations - this section is not needed.

## Phase 0: Research & Unknowns

### Research Tasks

1. **PDF Generation Library Evaluation**
   - **Question**: Which Python PDF library best supports our requirements (Unicode, QR codes, precise layout control)?
   - **Options**: ReportLab, WeasyPrint, FPDF, pdfkit
   - **Criteria**: Unicode support (Urdu/Arabic), QR code integration, table formatting, A4 layout control, performance
   - **Output**: Recommended library with rationale

2. **QR Code Generation Specifications**
   - **Question**: How to generate QR Code Version 2.0 (25x25 modules) at exactly 1.0x1.0 inch in PDF?
   - **Research**: QR code library options (qrcode, segno), version specification, size calculation for PDF embedding
   - **Output**: Implementation approach with code examples

3. **FBR Logo Asset Acquisition**
   - **Question**: Where to obtain the official FBR Digital Invoicing System logo?
   - **Research**: FBR documentation references, official sources, acceptable formats (PNG/SVG)
   - **Output**: Logo acquisition plan and storage location

4. **Unicode Font Handling**
   - **Question**: Which fonts support Urdu/Arabic characters in ReportLab PDFs?
   - **Research**: Font options (Noto Sans Arabic, Arial Unicode MS), ReportLab font registration, embedding requirements
   - **Output**: Font selection and integration approach

5. **PDF Response Patterns**
   - **Question**: Best practice for serving PDFs in FastAPI (streaming vs in-memory, content-disposition headers)?
   - **Research**: FastAPI Response types, browser compatibility, download vs inline display
   - **Output**: Implementation pattern with code examples

6. **Batch PDF Memory Management**
   - **Question**: How to efficiently generate 50-invoice PDFs without memory issues?
   - **Research**: ReportLab memory usage, streaming approaches, pagination strategies
   - **Output**: Memory-efficient batch generation approach

### Expected Outcomes

After Phase 0 research, we will have:
- Selected PDF generation library (likely ReportLab) with justification
- QR code generation approach with precise size specifications
- Font selection for Unicode support
- API response pattern for PDF delivery
- Memory management strategy for batch generation
- FBR logo acquisition plan

## Phase 1: Design & Contracts

### Data Model

**Note**: No new database models required. PDF generation uses existing `AutomationInvoice` model.

**Data Flow**:
1. Frontend requests PDF for invoice ID(s)
2. Backend validates user ownership and invoice status
3. Backend retrieves invoice data from `AutomationInvoice.invoice_data` and `fbr_response`
4. PDF service generates PDF with invoice data, logo, and QR code
5. Backend returns PDF as binary response
6. Frontend triggers download or opens in new tab

**Key Data Points**:
- **Input**: Invoice UUID(s), user authentication token
- **Processing**: Invoice data (JSON), FBR response (USIN), logo image, QR code generation
- **Output**: PDF binary stream with appropriate headers

### API Contracts

**Endpoint 1: Generate Single Invoice PDF**
```
GET /api/v1/automation/invoices/{invoice_id}/pdf
```
- **Authentication**: Required (JWT)
- **Authorization**: User must own the invoice
- **Validation**: Invoice must have status "submitted" and valid USIN
- **Response**: PDF binary (application/pdf)
- **Headers**: Content-Disposition: attachment; filename="Invoice-{number}-{date}.pdf"
- **Error Cases**: 404 (not found), 403 (not authorized), 400 (invalid status)

**Endpoint 2: Generate Batch Invoice PDF**
```
POST /api/v1/automation/invoices/batch-pdf
Body: { "invoice_ids": ["uuid1", "uuid2", ...] }
```
- **Authentication**: Required (JWT)
- **Authorization**: User must own all invoices
- **Validation**: Max 50 invoices, all must be "submitted" with valid USIN
- **Response**: PDF binary (application/pdf)
- **Headers**: Content-Disposition: attachment; filename="Invoices-Batch-{timestamp}.pdf"
- **Error Cases**: 400 (limit exceeded, invalid status), 403 (not authorized), 404 (invoice not found)

### Service Layer Design

**PDFService** (`backend/src/services/pdf_service.py`):
- `generate_invoice_pdf(invoice: AutomationInvoice) -> bytes`: Generate single invoice PDF
- `generate_batch_pdf(invoices: list[AutomationInvoice]) -> bytes`: Generate batch PDF with page breaks
- `_create_invoice_page(canvas, invoice_data, fbr_response, page_num)`: Internal method to render one invoice
- `_add_fbr_compliance_elements(canvas, usin, x, y)`: Add logo and QR code to page
- `_generate_qr_code(usin: str) -> Image`: Generate QR code image from USIN
- `_format_invoice_table(canvas, items, x, y, width)`: Render line items table
- `_calculate_totals(invoice_data) -> dict`: Calculate and format totals

**Error Handling**:
- Missing logo file: Log error, raise HTTPException 500
- QR code generation failure: Log error, raise HTTPException 500
- Invalid invoice data: Log error, raise HTTPException 400
- Memory issues (batch): Log error, raise HTTPException 500

### Frontend Integration Points

**Components to Modify**:
1. **InvoiceDetail.tsx**: Add "Print Invoice" button, handle PDF download
2. **InvoiceTable.tsx**: Add checkbox selection, "Print Selected" button
3. **InvoiceList.tsx**: Manage selection state, batch print trigger

**New Component**:
- **PrintInvoiceButton.tsx**: Reusable button component with loading state, error handling

**API Service Updates** (`automationApi.ts`):
```typescript
export const printInvoice = async (invoiceId: string): Promise<Blob>
export const printBatchInvoices = async (invoiceIds: string[]): Promise<Blob>
```

**User Experience Flow**:
1. User clicks "Print" on invoice detail → Loading state → PDF downloads
2. User selects invoices → Clicks "Print Selected" → Validation → Loading → PDF downloads
3. Error states: Toast notifications for failures, disabled buttons for invalid invoices

### Testing Strategy

**Backend Tests**:
- Unit tests: PDF service methods (QR code generation, table formatting, totals calculation)
- Integration tests: API endpoints (auth, authorization, validation, PDF generation)
- Edge cases: Unicode characters, long product descriptions, 50-invoice batch, missing logo

**Frontend Tests**:
- Component tests: Print button rendering, loading states, error handling
- Integration tests: API calls, blob handling, download triggering
- User interaction tests: Checkbox selection, batch limit validation

### Performance Considerations

- **Single Invoice**: Target <3 seconds (ReportLab is fast for single-page documents)
- **Batch Processing**: Generate sequentially to control memory, progress tracking for UX
- **Caching**: No PDF caching (on-demand only per spec), but logo and font loaded once per request
- **Concurrency**: FastAPI async endpoints allow concurrent PDF generation for different users

### Security Considerations

- **Authentication**: JWT verification via existing middleware
- **Authorization**: User ID filtering in database queries (row-level security)
- **Input Validation**: Invoice ID format, batch size limit, status validation
- **Data Exposure**: Only user's own invoices accessible, no cross-user data leakage
- **Injection Prevention**: No user input in PDF content (all data from database)

## Next Steps

After completing this plan:
1. **Phase 0**: Execute research tasks, document findings in `research.md`
2. **Phase 1**: Create `data-model.md`, `contracts/pdf-api.yaml`, `quickstart.md`
3. **Phase 2**: Run `/sp.tasks` to generate implementation tasks from this plan
4. **Implementation**: Execute tasks in priority order (P1 → P2 → P3)

## Dependencies

- **Blocked by**: FBR logo asset acquisition (can use placeholder initially)
- **Blocks**: None (independent feature, no downstream dependencies)
- **Integrates with**: Existing automation system, authentication, invoice models

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Unicode rendering issues | High | Research and test fonts early, validate with sample Urdu/Arabic data |
| Batch PDF memory usage | Medium | Implement streaming/sequential generation, test with 50 invoices |
| QR code scanning failures | High | Validate QR code specs against FBR requirements, test with multiple readers |
| Missing FBR logo | Medium | Use placeholder initially, document logo requirements clearly |
| Performance degradation | Medium | Implement timeouts, monitor generation times, optimize if needed |
