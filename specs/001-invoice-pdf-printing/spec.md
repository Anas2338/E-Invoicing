# Feature Specification: Invoice PDF Printing with FBR Compliance

**Feature Branch**: `001-invoice-pdf-printing`  
**Created**: 2026-04-14  
**Status**: Draft  
**Input**: User description: "PDF Invoice Printing with FBR Compliance - Users need to print submitted/posted invoices in PDF format with FBR-compliant logo and QR codes. Support single invoice printing and batch printing of multiple selected invoices. Each printed invoice must include the FBR Digital Invoicing System logo and a QR code (Version 2.0, 25x25, 1.0x1.0 inch dimensions) containing the FBR-issued invoice number (USIN) for verification purposes."

## Clarifications

### Session 2026-04-14

- Q: PDF Storage Strategy → A: Generate PDFs on-demand each time a user requests to print (no storage)
- Q: QR Code Content Format → A: USIN only as plain text (e.g., "7000007DI1747119701593")
- Q: Non-Submitted Invoice Print Behavior → A: Show error message and disable print button for invoices without USIN
- Q: Batch Print Invoice Ordering → A: Selection order (order user clicked checkboxes)
- Q: Maximum Batch Print Limit → A: 50 invoices maximum

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Print Single Submitted Invoice (Priority: P1)

A user who has successfully submitted an invoice to FBR needs to generate a printable PDF version of that invoice for their records, customer delivery, or audit purposes. The PDF must include all invoice details along with FBR-mandated compliance elements (logo and QR code).

**Why this priority**: This is the core MVP functionality. Every submitted invoice needs a printable version for legal compliance and business operations. Without this, users cannot provide proper documentation to customers or maintain audit trails.

**Independent Test**: Can be fully tested by submitting a single invoice through the automation system, then clicking a "Print" or "Download PDF" button on the invoice detail page. The test delivers immediate value by producing a compliant, printable invoice document.

**Acceptance Scenarios**:

1. **Given** a user has a submitted invoice with status "submitted" and a valid FBR response containing USIN, **When** they view the invoice detail page and click "Print Invoice", **Then** a PDF is generated containing all invoice data, FBR logo, and QR code with USIN
2. **Given** a user views an invoice detail page, **When** they click "Download PDF", **Then** the PDF file downloads to their device with filename format "Invoice-[InvoiceNumber]-[Date].pdf"
3. **Given** a submitted invoice with multiple line items, **When** PDF is generated, **Then** all line items are displayed in a formatted table with correct calculations
4. **Given** a user opens the generated PDF, **When** they scan the QR code with a QR reader, **Then** the QR code contains the FBR-issued USIN in readable format

---

### User Story 2 - Batch Print Multiple Invoices (Priority: P2)

A user needs to print multiple invoices at once for batch processing, monthly reporting, or bulk customer delivery. They should be able to select multiple invoices from the invoice list and generate a single PDF containing all selected invoices.

**Why this priority**: This significantly improves efficiency for users managing high volumes of invoices. While not essential for MVP, it's a common business need that reduces repetitive work and improves user experience.

**Independent Test**: Can be tested by selecting 3-5 submitted invoices from the invoice list using checkboxes, clicking "Print Selected", and verifying that a single PDF is generated with all invoices in sequence, each with proper page breaks and compliance elements.

**Acceptance Scenarios**:

1. **Given** a user is on the invoice list page with multiple submitted invoices, **When** they select 3 invoices using checkboxes and click "Print Selected", **Then** a single PDF is generated containing all 3 invoices with page breaks between them
2. **Given** a user has selected 10 invoices for batch printing, **When** the PDF is generated, **Then** each invoice in the PDF includes its own FBR logo and unique QR code
3. **Given** a user selects invoices with different dates and customers, **When** batch PDF is generated, **Then** invoices are ordered by selection order (the sequence in which checkboxes were clicked)
4. **Given** a user has not selected any invoices, **When** they click "Print Selected", **Then** they see an error message "Please select at least one invoice to print"

---

### User Story 3 - Print Options and Preview (Priority: P3)

Users need flexibility in how they print invoices, including the ability to preview before downloading, choose between opening in browser vs downloading, and potentially customize print settings.

**Why this priority**: These are quality-of-life improvements that enhance user experience but aren't critical for core functionality. They can be added after the basic printing works reliably.

**Independent Test**: Can be tested by clicking print on any invoice and verifying that a preview modal appears, allowing users to review the PDF before committing to download or print.

**Acceptance Scenarios**:

1. **Given** a user clicks "Print Invoice", **When** the PDF is ready, **Then** they see options to "Download" or "Open in New Tab"
2. **Given** a user selects "Open in New Tab", **When** the PDF opens, **Then** they can use browser print functionality (Ctrl+P) to print directly
3. **Given** a user is generating a batch PDF of 20+ invoices, **When** generation is in progress, **Then** they see a progress indicator showing "Generating PDF: X of Y invoices"

---

### Edge Cases

- What happens when a user tries to print an invoice that hasn't been submitted to FBR yet (no USIN available)? → Print button is disabled and error message is shown
- How does the system handle invoices with very long product descriptions or many line items that might cause pagination issues?
- What happens if the FBR logo image file is missing or corrupted?
- How does the system handle special characters or non-English text in invoice data (buyer/seller names, addresses)?
- What happens when a user tries to batch print more than 50 invoices at once? → System shows error message enforcing the 50 invoice limit
- How does the system handle invoices with status "failed" or "blocked" - should they be printable?
- What happens if QR code generation fails for a specific invoice?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate PDF documents for invoices with status "submitted" that contain a valid FBR response with USIN
- **FR-002**: System MUST include the FBR Digital Invoicing System logo on each printed invoice
- **FR-003**: System MUST generate a QR code (Version 2.0, 25x25 modules, 1.0x1.0 inch dimensions) containing the FBR-issued USIN for each invoice
- **FR-004**: System MUST display all invoice header information including invoice number, date, seller details, buyer details, and registration types
- **FR-005**: System MUST display all invoice line items in a formatted table showing HS code, product description, quantity, unit of measure, rates, taxes, and totals
- **FR-006**: System MUST calculate and display invoice totals including subtotal, sales tax, withholding tax, extra tax, further tax, FED, and grand total
- **FR-007**: System MUST support single invoice PDF generation from the invoice detail view
- **FR-008**: System MUST support batch PDF generation for multiple selected invoices from the invoice list view
- **FR-009**: System MUST provide a way for users to select multiple invoices (checkboxes or similar selection mechanism)
- **FR-010**: System MUST generate PDF filenames in a consistent format that includes invoice number and date
- **FR-011**: System MUST insert page breaks between invoices in batch PDF generation
- **FR-012**: System MUST handle invoices with varying numbers of line items (1 to 50+) with proper pagination
- **FR-013**: System MUST display appropriate error messages when PDF generation fails
- **FR-014**: System MUST prevent printing of invoices without valid USIN (not yet submitted or submission failed)
- **FR-015**: System MUST position the FBR logo and QR code in the footer or designated area of each invoice page
- **FR-016**: System MUST ensure QR codes are scannable and contain accurate USIN data
- **FR-017**: System MUST support PDF generation for invoices containing Unicode characters (Urdu, Arabic, special symbols)
- **FR-018**: System MUST enforce a maximum batch print limit of 50 invoices per request
- **FR-019**: System MUST generate PDFs on-demand without storing generated PDF files

### Key Entities

- **Invoice PDF Document**: A formatted PDF representation of one or more submitted invoices, containing all invoice data, FBR compliance elements (logo and QR code), and proper formatting for printing or digital distribution
- **QR Code**: A 2D barcode (Version 2.0, 25x25 modules, 1.0x1.0 inch) encoding the FBR-issued USIN, enabling verification of invoice authenticity
- **FBR Logo**: The official Digital Invoicing System logo image required by FBR regulations to be printed on all invoices
- **USIN (Unique Sales Invoice Number)**: The FBR-issued identifier returned in the submission response, used for invoice verification and encoded in the QR code

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can generate a single invoice PDF in under 3 seconds for invoices with up to 20 line items
- **SC-002**: Users can successfully generate batch PDFs containing up to 50 invoices without system timeout or errors
- **SC-003**: 100% of generated PDFs include a scannable QR code that correctly encodes the invoice USIN
- **SC-004**: 100% of generated PDFs include the FBR Digital Invoicing System logo in the correct position and dimensions
- **SC-005**: Users can successfully download and open generated PDFs in standard PDF readers (Adobe Reader, browser PDF viewers, mobile PDF apps)
- **SC-006**: Generated PDFs are print-ready with proper margins, page breaks, and formatting when printed on A4 or Letter size paper
- **SC-007**: QR codes in printed invoices remain scannable when printed at standard printer resolutions (300 DPI or higher)
- **SC-008**: Users report successful use of printed invoices for customer delivery and audit purposes without compliance issues

## Assumptions

- The FBR Digital Invoicing System logo will be provided as a high-resolution image file (PNG or SVG format) and stored in the project assets
- All submitted invoices in the database have a valid `fbr_response` field containing the USIN
- The QR code will contain only the USIN as plain text
- Standard commercial invoice layout is acceptable for FBR compliance (no specific template mandated beyond logo and QR code requirements)
- PDF generation will be handled server-side for security and consistency
- Users have appropriate permissions to view and print invoices they have submitted
- The system will use standard A4 page size (210mm x 297mm) for PDF generation
- Batch printing is limited to a maximum of 50 invoices to prevent performance issues and ensure completion within reasonable timeframes
