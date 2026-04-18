# Tasks: Invoice PDF Printing with FBR Compliance

**Input**: Design documents from `/specs/001-invoice-pdf-printing/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/pdf-api.yaml

**Tests**: Tests are NOT included as they were not explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`
- Backend: Python 3.11+, FastAPI, ReportLab
- Frontend: TypeScript, Next.js 16+ App Router

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and asset acquisition

- [x] T001 Add PDF generation dependencies to backend/pyproject.toml (reportlab>=4.0.0, qrcode>=7.4.2, Pillow>=10.0.0)
- [x] T002 Install dependencies using uv sync in backend directory
- [x] T003 [P] Create backend/src/assets/ directory for logo and font files
- [x] T004 [P] Download Noto Sans Arabic font to backend/src/assets/NotoSansArabic-Regular.ttf
- [x] T005 [P] Obtain FBR Digital Invoicing System logo and save to backend/src/assets/fbr_logo.png (or create placeholder)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core PDF service infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Create PDFService class skeleton in backend/src/services/pdf_service.py with imports and class structure
- [x] T007 [P] Implement font registration method _register_fonts() in backend/src/services/pdf_service.py
- [x] T008 [P] Implement logo loading method _load_fbr_logo() in backend/src/services/pdf_service.py with error handling
- [x] T009 [P] Implement QR code generation method _generate_qr_code(usin: str) in backend/src/services/pdf_service.py (Version 2.0, 25x25 modules, 1.0x1.0 inch)
- [x] T010 Implement invoice header rendering method _render_invoice_header(canvas, invoice_data, x, y) in backend/src/services/pdf_service.py
- [x] T011 Implement line items table rendering method _render_line_items_table(canvas, items, x, y, width) in backend/src/services/pdf_service.py
- [x] T012 Implement totals rendering method _render_totals(canvas, invoice_data, x, y) in backend/src/services/pdf_service.py
- [x] T013 Implement FBR compliance elements method _add_fbr_compliance_elements(canvas, usin, x, y) in backend/src/services/pdf_service.py (logo + QR code)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Print Single Submitted Invoice (Priority: P1) 🎯 MVP

**Goal**: Users can generate and download a PDF for a single submitted invoice with all invoice data, FBR logo, and QR code containing USIN

**Independent Test**: Submit an invoice through automation system, navigate to invoice detail page, click "Print Invoice" button, verify PDF downloads with correct filename and contains all invoice data, FBR logo, and scannable QR code

### Backend Implementation for User Story 1

- [x] T014 [US1] Implement generate_invoice_pdf(invoice: AutomationInvoice) method in backend/src/services/pdf_service.py using foundational methods
- [x] T015 [US1] Create PDF API router file backend/src/api/v1/automation/pdf.py with FastAPI router setup
- [x] T016 [US1] Implement GET /invoices/{invoice_id}/pdf endpoint in backend/src/api/v1/automation/pdf.py with JWT auth, authorization, validation, and StreamingResponse
- [x] T017 [US1] Add error handling for missing logo, invalid status, missing USIN in backend/src/api/v1/automation/pdf.py
- [x] T018 [US1] Register PDF router in backend/src/api/v1/automation/__init__.py
- [x] T019 [US1] Add logging for PDF generation events (start, success, failure) in backend/src/services/pdf_service.py

### Frontend Implementation for User Story 1

- [x] T020 [P] [US1] Add printInvoice(invoiceId: string) API function in frontend/src/services/automationApi.ts
- [x] T021 [P] [US1] Create PrintInvoiceButton component in frontend/src/components/automation/PrintInvoiceButton.tsx with loading state and error handling
- [x] T022 [US1] Add print button to InvoiceDetail component in frontend/src/components/automation/InvoiceDetail.tsx
- [x] T023 [US1] Implement PDF download logic (blob handling, filename generation) in PrintInvoiceButton component
- [x] T024 [US1] Add disabled state for non-submitted invoices in PrintInvoiceButton component
- [x] T025 [US1] Add error toast notifications for PDF generation failures in PrintInvoiceButton component

**Checkpoint**: At this point, User Story 1 should be fully functional - users can print single invoices independently

---

## Phase 4: User Story 2 - Batch Print Multiple Invoices (Priority: P2)

**Goal**: Users can select multiple invoices from the list and generate a single PDF containing all selected invoices with page breaks, ordered by selection sequence

**Independent Test**: Navigate to invoice list, select 3-5 submitted invoices using checkboxes, click "Print Selected" button, verify single PDF downloads with all invoices in selection order, each with page breaks and compliance elements

### Backend Implementation for User Story 2

- [x] T026 [US2] Implement generate_batch_pdf(invoices: list[AutomationInvoice]) method in backend/src/services/pdf_service.py with sequential generation and page breaks
- [x] T027 [US2] Create BatchPdfRequest schema in backend/src/schemas/automation.py with invoice_ids array validation (1-50 items)
- [x] T028 [US2] Implement POST /invoices/batch-pdf endpoint in backend/src/api/v1/automation/pdf.py with batch validation and selection order preservation
- [x] T029 [US2] Add batch size validation (max 50 invoices) in backend/src/api/v1/automation/pdf.py
- [x] T030 [US2] Add batch authorization check (all invoices belong to user) in backend/src/api/v1/automation/pdf.py
- [x] T031 [US2] Add logging for batch PDF generation with invoice count in backend/src/services/pdf_service.py

### Frontend Implementation for User Story 2

- [x] T032 [P] [US2] Add printBatchInvoices(invoiceIds: string[]) API function in frontend/src/services/automationApi.ts
- [x] T033 [P] [US2] Add checkbox selection state management to InvoiceTable component in frontend/src/components/automation/InvoiceTable.tsx
- [x] T034 [US2] Add "Select All" checkbox to InvoiceTable header in frontend/src/components/automation/InvoiceTable.tsx
- [x] T035 [US2] Add individual invoice checkboxes to each row in InvoiceTable component
- [x] T036 [US2] Add "Print Selected" button to InvoiceTable component with disabled state when no selection
- [x] T037 [US2] Implement batch print handler with 50-invoice limit validation in InvoiceTable component
- [x] T038 [US2] Add error message for exceeding 50-invoice limit in InvoiceTable component
- [x] T039 [US2] Add error message for empty selection in InvoiceTable component
- [x] T040 [US2] Clear selection after successful batch print in InvoiceTable component

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - single and batch printing functional

---

## Phase 5: User Story 3 - Print Options and Preview (Priority: P3)

**Goal**: Users have flexibility in how they print invoices with preview options, download vs open in browser choice, and progress indicators for batch operations

**Independent Test**: Click print on any invoice, verify preview modal appears with "Download" and "Open in New Tab" options, test both options work correctly, verify progress indicator shows for batch operations with 20+ invoices

### Backend Implementation for User Story 3

- [x] T041 [US3] Add support for inline Content-Disposition header (open in browser) in backend/src/api/v1/automation/pdf.py GET endpoint
- [x] T042 [US3] Add query parameter for disposition type (attachment vs inline) in backend/src/api/v1/automation/pdf.py

### Frontend Implementation for User Story 3

- [x] T043 [P] [US3] Create PrintPreviewModal component in frontend/src/components/automation/PrintPreviewModal.tsx
- [x] T044 [P] [US3] Add "Download" and "Open in New Tab" buttons to PrintPreviewModal component
- [x] T045 [US3] Update PrintInvoiceButton to show preview modal instead of direct download in frontend/src/components/automation/PrintInvoiceButton.tsx
- [x] T046 [US3] Implement "Open in New Tab" handler using inline disposition in PrintPreviewModal component
- [x] T047 [US3] Add progress indicator component for batch PDF generation in frontend/src/components/automation/BatchPrintProgress.tsx
- [x] T048 [US3] Show progress indicator when generating batch PDFs with 20+ invoices in InvoiceTable component
- [x] T049 [US3] Update progress indicator with "Generating PDF: X of Y invoices" message during batch generation

**Checkpoint**: All user stories should now be independently functional with enhanced UX features

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and production readiness

- [x] T050 [P] Add comprehensive error handling for edge cases (long product descriptions, Unicode characters, missing fields) in backend/src/services/pdf_service.py
- [x] T051 [P] Add timeout handling for batch PDF generation (180 seconds) in backend/src/api/v1/automation/pdf.py
- [x] T052 [P] Optimize memory usage for 50-invoice batch generation in backend/src/services/pdf_service.py
- [x] T053 [P] Add validation for invoice data structure before PDF generation in backend/src/services/pdf_service.py
- [x] T054 [P] Update quickstart.md with setup instructions and troubleshooting guide in specs/001-invoice-pdf-printing/quickstart.md
- [x] T055 [P] Add API documentation comments to PDF endpoints in backend/src/api/v1/automation/pdf.py
- [x] T056 [P] Verify Unicode character rendering with sample Urdu/Arabic invoice data
- [x] T057 [P] Test QR code scannability with multiple QR readers (phone camera, dedicated apps)
- [x] T058 [P] Verify PDF opens correctly in multiple PDF readers (Adobe, Chrome, Firefox, mobile)
- [x] T059 Security review: Verify JWT authentication, authorization, and input validation across all endpoints
- [x] T060 Performance testing: Generate 50-invoice batch and verify completion under 150 seconds
- [x] T061 Run through quickstart.md validation steps to ensure developer setup works correctly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1 (uses same PDF service methods)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Enhances US1 and US2 but doesn't block them

### Within Each User Story

- Backend implementation before frontend (API must exist for frontend to call)
- Core PDF generation methods before API endpoints
- API endpoints before frontend integration
- Component creation before integration into pages
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Backend and frontend tasks within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members
- All Polish tasks marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Backend tasks that can run in parallel:
Task T019: "Add logging for PDF generation events"

# Frontend tasks that can run in parallel:
Task T020: "Add printInvoice API function in automationApi.ts"
Task T021: "Create PrintInvoiceButton component"

# After T016 (API endpoint) completes, these can proceed together:
Task T022: "Add print button to InvoiceDetail"
Task T023: "Implement PDF download logic"
Task T024: "Add disabled state for non-submitted invoices"
Task T025: "Add error toast notifications"
```

---

## Parallel Example: User Story 2

```bash
# Backend tasks that can run in parallel after T026 completes:
Task T027: "Create BatchPdfRequest schema"
Task T031: "Add logging for batch PDF generation"

# Frontend tasks that can run in parallel:
Task T032: "Add printBatchInvoices API function"
Task T033: "Add checkbox selection state management"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T013) - CRITICAL
3. Complete Phase 3: User Story 1 (T014-T025)
4. **STOP and VALIDATE**: Test single invoice printing independently
5. Deploy/demo if ready

**MVP Deliverable**: Users can print single submitted invoices with FBR-compliant PDFs

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo (Batch printing added)
4. Add User Story 3 → Test independently → Deploy/Demo (Enhanced UX)
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T013)
2. Once Foundational is done:
   - Developer A: User Story 1 (T014-T025)
   - Developer B: User Story 2 (T026-T040)
   - Developer C: User Story 3 (T041-T049)
3. Stories complete and integrate independently
4. Team collaborates on Polish phase (T050-T061)

---

## Task Summary

**Total Tasks**: 61
- Phase 1 (Setup): 5 tasks
- Phase 2 (Foundational): 8 tasks (BLOCKING)
- Phase 3 (User Story 1 - MVP): 12 tasks
- Phase 4 (User Story 2): 15 tasks
- Phase 5 (User Story 3): 9 tasks
- Phase 6 (Polish): 12 tasks

**Parallel Opportunities**: 28 tasks marked [P] can run in parallel within their phase

**MVP Scope**: Phases 1-3 (25 tasks) deliver core single invoice printing functionality

**Independent Test Criteria**:
- **US1**: Print single invoice → PDF downloads with all data, logo, QR code
- **US2**: Select multiple invoices → Single PDF with all invoices in order
- **US3**: Click print → Preview modal with download/open options

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- FBR logo must be obtained before production deployment (placeholder OK for development)
- Test QR code scannability with real devices before production
- Verify Unicode rendering with actual Urdu/Arabic invoice data
