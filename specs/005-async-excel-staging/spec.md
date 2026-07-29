# Feature Specification: Async Excel Staging with Inline Error Correction

**Feature Branch**: `005-async-excel-staging`  
**Created**: 2026-07-27  
**Status**: Draft  
**Input**: User description: "Replace the current all-or-nothing manual Excel upload flow with an async, persistent staging workflow where users can edit errored invoices directly in the UI instead of re-uploading the entire Excel file."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload Excel and View All Parsed Invoices (Priority: P1)

A business user needs to create multiple sale invoices at once. They download the Excel template, fill it with invoice data, and upload it. Instead of the system rejecting the entire file because of a few mistakes, the system parses ALL rows and displays them in a spreadsheet-like table. Valid rows are shown with green indicators; rows with errors have red-highlighted cells showing exactly which fields need correction. The user can see all their data at a glance.

**Why this priority**: This is the foundational change — without it, the user cannot proceed to editing. It replaces the broken all-or-nothing experience with a resilient, transparent one.

**Independent Test**: Upload an Excel file with a mix of valid and invalid rows. Verify that all rows appear in the grid, valid rows show green checkmarks, and errored rows show red error indicators on the specific fields that failed validation.

**Acceptance Scenarios**:

1. **Given** a user has an Excel file with 10 invoice rows (7 valid, 3 with errors like missing buyer name, negative quantity, invalid income tax code), **When** they select the file and click "Upload & Parse", **Then** the system displays all 10 rows in an editable grid with 7 marked valid and 3 marked with field-specific error highlights.
2. **Given** a user uploads an Excel file where all rows are valid, **When** parsing completes, **Then** all rows show green valid indicators and an "Upload All" button is immediately available.
3. **Given** a user uploads an Excel file where every single row has errors, **When** parsing completes, **Then** all rows show error indicators, the "Upload All" button is disabled, and a summary shows "10 rows have errors."
4. **Given** a user uploads an Excel file with multi-item invoices (multiple rows sharing the same invoice number), **When** parsing completes, **Then** rows with the same invoice number are visually grouped together in the grid.

---

### User Story 2 - Edit Errors Directly in the Grid (Priority: P1)

After seeing which cells have errors, the user clicks on an errored cell (e.g., the quantity field showing "-1") and edits it directly inline — just like editing a spreadsheet cell. They change the value, press Enter, and the cell's red highlight disappears (pending recheck). The user can fix multiple cells across different rows without needing to download, edit, and re-upload the Excel file.

**Why this priority**: This is the core value proposition — inline editing eliminates the frustrating re-upload cycle. Without this, the staging grid is just a read-only error report.

**Independent Test**: Click an errored cell in the grid, change its value, press Enter. Verify the cell shows the new value and the red error indicator is cleared (pending recheck). Refresh the page and verify the change was persisted to the server.

**Acceptance Scenarios**:

1. **Given** a row has an error "buyer_business_name is required" on the buyer name cell, **When** the user clicks the empty buyer name cell, types a business name, and presses Enter, **Then** the cell displays the new value, the red highlight is removed, and the change is persisted to the backend.
2. **Given** a user edits a quantity field from "-1" to "5", **When** they click away (blur) from the cell, **Then** the value "5" is saved and the error indicator for quantity is cleared.
3. **Given** a user edits multiple fields in a row, **When** they refresh the page, **Then** all their edits are preserved and visible in the grid.
4. **Given** an errored cell has a dropdown-constrained field (e.g., invoice_type, buyer_province, income_tax), **When** the user clicks the cell, **Then** a dropdown with valid options appears instead of a free-text input.

---

### User Story 3 - Recheck Corrected Rows (Priority: P2)

After fixing errors in the grid, the user clicks a "Recheck" button. The system re-validates only the rows that had errors (or were edited). Rows whose errors have been fully resolved turn green and become valid. Rows that still have issues show updated error messages. The user sees a summary of how many errors remain. This cycle of editing and rechecking continues until all errors are resolved.

**Why this priority**: The recheck loop is the mechanism that moves rows from "errored" to "valid." It is the bridge between editing and final upload. It is P2 because a user could theoretically fix everything perfectly on first edit, but in practice multiple recheck cycles are needed.

**Independent Test**: Upload a file with errors, edit some cells to fix issues, click "Recheck." Verify that fixed rows become valid, still-errored rows show updated errors, and the valid/errored count updates correctly.

**Acceptance Scenarios**:

1. **Given** 3 rows have errors, and the user fixes 2 of them correctly, **When** they click "Recheck", **Then** the 2 fixed rows become valid (green checkmark), the 1 still-errored row retains its error indicators, and the summary updates to "1 row has errors."
2. **Given** all rows are valid after editing, **When** the user clicks "Recheck", **Then** the system confirms "All rows are valid" and enables the "Upload All" button.
3. **Given** a user edits a cell but introduces a NEW error (e.g., changes invoice_date to a future date), **When** they click "Recheck", **Then** that cell now shows the new error message and the row remains errored.
4. **Given** recheck is in progress, **When** the user views the grid, **Then** they see a loading indicator and the grid is temporarily non-editable until recheck completes.

---

### User Story 4 - Upload All Valid Invoices (Priority: P2)

When all rows are valid (no errors remain after recheck), the "Upload All" button becomes enabled. The user clicks it, and all invoices are created in the system with DRAFT status. The temporary staging data is automatically cleaned up (deleted from the database). The user sees a success summary showing how many invoices were created, with a link to view them in the invoice history. The temporary staging table becomes empty.

**Why this priority**: This is the end goal of the entire flow — actually creating the invoices. It is P2 because the editing and rechecking flow (P1) can be fully built and tested independently; commit is the final step.

**Independent Test**: With all rows valid, click "Upload All." Verify that all invoices appear in the invoice history page as DRAFT, and the staging session is deleted (returning to the upload page shows a fresh file picker with no residual data).

**Acceptance Scenarios**:

1. **Given** all 10 rows are valid, **When** the user clicks "Upload All", **Then** 10 invoices are created in the main invoices table with DRAFT status, the staging session and all its rows are deleted from the database, and a success message shows "10 invoices created as DRAFT."
2. **Given** invoices span multiple items (multi-row invoices sharing the same invoice number), **When** "Upload All" is clicked, **Then** each unique invoice number becomes one invoice with multiple line items.
3. **Given** an invoice number already exists in the user's invoice history, **When** "Upload All" is clicked at commit time, **Then** that specific invoice is flagged as failed with a clear "already exists" message, while other invoices succeed.
4. **Given** commit is in progress, **When** the user views the screen, **Then** they see a progress indicator and cannot edit the grid.

---

### User Story 5 - Cancel and Discard Staging Session (Priority: P3)

At any point during the review/edit process, the user can click a "Cancel" button to abandon the entire staging session. The temporary staging data is immediately deleted from the database, and the user is returned to the initial upload screen with the file picker. No invoices are created. The staging table becomes empty.

**Why this priority**: Cancel is a safety valve — important for user confidence but not core to the happy path. Users need to know they can back out without leaving orphaned data.

**Independent Test**: Upload a file, edit some cells, click "Cancel." Verify the staging session is deleted from the database, the grid disappears, and the file picker is shown again. Verify no invoices were created.

**Acceptance Scenarios**:

1. **Given** a user is in the review grid with 10 rows (some valid, some errored), **When** they click "Cancel", **Then** the entire staging session is deleted from the database, no invoices are created, and the user is returned to the initial file upload view.
2. **Given** a user cancels while a recheck is in progress, **When** the cancel is processed, **Then** the recheck is stopped and the session is deleted.
3. **Given** a user clicks "Cancel", **When** the cancel completes, **Then** a brief message says "Upload cancelled" and the file picker is clean and ready for a new upload.

---

### User Story 6 - Resume Session After Navigation or Logout (Priority: P2)

The upload, editing, and recheck process may take time. The user can navigate to other pages in the application, close their browser, or even log out — and when they return to the Excel upload page, the system automatically detects their active staging session and resumes exactly where they left off. The grid shows all their data and edits intact.

**Why this priority**: Session persistence is what makes the "async" nature useful. Without it, any accidental navigation would lose all work. This is P2 because the core editing flow works without persistence, but persistence is essential for real-world usability.

**Independent Test**: Upload a file, edit some cells, navigate to the Dashboard, then return to the Excel upload page. Verify the grid reappears with all edits intact. Logout, login, navigate to Excel upload — verify the session resumes.

**Acceptance Scenarios**:

1. **Given** a user has an active staging session with edited rows, **When** they navigate to the Dashboard and then return to the Excel upload page, **Then** the grid automatically loads with their session and shows all edits intact.
2. **Given** a user has an active staging session, **When** they log out and log back in, then navigate to the Excel upload page, **Then** the system detects the active session and displays it.
3. **Given** a user has an active staging session, **When** they see an indicator showing "You have an in-progress Excel upload from [filename]" with options to Resume or Dismiss, **Then** clicking Resume opens the grid; clicking Dismiss cancels the session.
4. **Given** a user's staging session is older than 7 days, **When** they return to the Excel upload page, **Then** the expired session is not shown (auto-cleaned) and they see a fresh upload screen.

---

### Edge Cases

- **Empty file**: When the Excel file contains only the sample row (INV-001) or no data rows, the system returns a clear message: "No invoice data found in file. Please fill the template and try again."
- **Very large file (500+ rows)**: The grid handles large datasets with scrollable viewport. Performance remains acceptable for files up to 1,000 rows.
- **New upload replaces existing session**: When a user uploads a new Excel file while they already have an active staging session, the existing session is automatically cancelled (deleted) and replaced with the new one. Only one active session per user.
- **Duplicate invoice numbers within the same file**: Flagged as errors during recheck — each duplicate row shows an error on the invoice_number field.
- **Invoice number already in main database**: Checked at commit time (not during initial parse) because the user might change the invoice number in the grid. If an invoice number already exists at commit time, that specific invoice fails while others succeed.
- **Network failure during upload**: If the network drops during file upload, the user sees an error and can retry. No partial session is created.
- **Network failure during commit**: If the network drops during commit, the session remains with its data intact and the user can retry the commit.
- **Saved item deleted between upload and commit**: If a user's saved item is deleted after the Excel was parsed, the recheck catches it and shows an error on the `saved_item_code` field.
- **User edits a cell to an invalid value**: The cell does not immediately show an error — the error appears after the user clicks "Recheck." This keeps the editing experience smooth and prevents flickering error states while typing.
- **Multi-item invoices with inconsistent header fields**: If rows for the same invoice number have different invoice dates or buyer info, the recheck flags the inconsistent rows with errors.

## Clarifications

### Session 2026-07-27

- Q: When the user clicks "Recheck", which rows should the system re-validate? → A: All rows that have been edited since the last recheck (or initial parse), whether they were valid or errored before. This catches newly introduced errors on previously valid rows.

## Requirements *(mandatory)*

### Functional Requirements

**File Upload & Parsing:**

- **FR-001**: System MUST accept `.xlsx` file uploads up to 10 MB in size.
- **FR-002**: System MUST validate file security and structure before parsing.
- **FR-003**: System MUST parse ALL rows from the Excel file without failing on validation errors — every row is captured whether valid or errored.
- **FR-004**: System MUST capture field-level validation errors per row (e.g., `{"buyer_business_name": ["is required"], "quantity": ["must be greater than 0"]}`).
- **FR-005**: System MUST store all parsed rows and their error state in a persistent staging session tied to the authenticated user.

**Staging Grid Display:**

- **FR-006**: System MUST display all parsed rows in a spreadsheet-like table with one row per Excel row.
- **FR-007**: System MUST visually distinguish valid rows (green indicator) from errored rows (red indicator).
- **FR-008**: System MUST highlight specific errored cells with red background/border and show error messages on hover or focus.
- **FR-009**: System MUST group rows sharing the same invoice number visually (adjacent rows with a group indicator or shared header).
- **FR-010**: System MUST display a summary showing total rows, valid count, and errored count.

**Inline Editing:**

- **FR-011**: Users MUST be able to click any cell in the grid to edit its value inline (input field appears on click).
- **FR-012**: For constrained fields (invoice_type, buyer_province, buyer_registration_type, income_tax), the edit mode MUST show a dropdown with valid options.
- **FR-013**: For numeric fields (quantity, value_sales_excluding_st, discount, etc.), the edit mode MUST accept decimal numbers.
- **FR-014**: Changes made to a cell MUST be persisted to the backend immediately (on blur or Enter) so they survive page refresh. The backend MUST track that the row has been edited since the last recheck (e.g., a dirty flag) so Recheck knows which rows to re-validate.
- **FR-015**: When a cell value is changed, the cell's error indicator MUST be cleared (pending recheck) since the error may have been resolved.

**Recheck:**

- **FR-016**: Users MUST be able to trigger a "Recheck" that re-validates all rows that have been edited since the last recheck (or initial parse), regardless of whether they were previously valid or errored.
- **FR-017**: Recheck MUST run the same validation rules as the initial parse (field presence, value ranges, date validity, saved item existence, etc.).
- **FR-018**: After recheck, rows that pass all validations MUST be marked valid; rows that still fail MUST show updated error messages.
- **FR-019**: During recheck, the grid MUST be read-only and show a loading indicator.
- **FR-020**: When recheck completes with zero errors, the "Upload All" button MUST become enabled.

**Commit (Upload All):**

- **FR-021**: "Upload All" button MUST be enabled only when all rows are valid (zero errored rows after latest recheck).
- **FR-022**: System MUST group valid rows by invoice number and create one invoice per unique invoice number, with line items from each row in that group.
- **FR-023**: All created invoices MUST have DRAFT status.
- **FR-024**: System MUST re-check for duplicate invoice numbers against the main invoices table at commit time.
- **FR-025**: After successful commit, the staging session and all its rows MUST be deleted from the database — the data is now in the main invoices table and the temporary staging table becomes empty.
- **FR-026**: System MUST return a summary showing total invoices created, any that failed, and a link to invoice history.

**Cancel:**

- **FR-027**: Users MUST be able to cancel the staging session at any time (during review, during recheck, etc.).
- **FR-028**: On cancel, the staging session and all its rows MUST be deleted from the database immediately — the temporary staging table becomes empty.
- **FR-029**: After cancel, the user MUST be returned to the initial file upload view.

**Session Persistence & Recovery:**

- **FR-030**: The staging session MUST survive browser close, page navigation, and logout/login.
- **FR-031**: When a user navigates to the Excel upload page, the system MUST check for an active staging session and automatically load it if found.
- **FR-032**: Only one active staging session MAY exist per user at a time. Uploading a new file replaces any existing active session.
- **FR-033**: Staging sessions older than 7 days MUST be considered expired and not shown for recovery.

### Key Entities

- **Excel Staging Session**: Represents one file upload that is in progress. Contains user ownership, original filename, status (parsing, ready-for-review, rechecking, committing, cancelled), total/valid/errored row counts, and a collection of staging rows. Temporary — deleted after commit or cancel.
- **Staging Row**: Represents one row from the uploaded Excel file. Contains the parsed field values (all 16 template columns: invoice_number, invoice_type, invoice_date, buyer fields, item code, quantity, amounts, tax info), computed fields (product description from saved item lookup, calculated tax amounts), seller information (captured at parse time), and a dictionary of field-level validation errors. Belongs to exactly one staging session.
- **Invoice** (existing): The final output — each unique invoice number from the staging session becomes one Invoice with DRAFT status in the main invoices table after successful commit.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can upload an Excel file with mixed valid/invalid rows and see ALL rows displayed in the grid within 10 seconds for files up to 500 rows.
- **SC-002**: Users can correct validation errors entirely within the UI — zero need to re-download and re-upload the Excel file.
- **SC-003**: Users can complete an editing cycle (edit cells → recheck → see updated results) in under 5 seconds for typical files (up to 100 rows).
- **SC-004**: 100% of cell edits survive page navigation and browser refresh — no work is lost.
- **SC-005**: 100% of staging sessions are cleaned up (deleted from database) after either successful commit or cancel — no orphaned staging data remains.
- **SC-006**: Users can resume an in-progress staging session after logging out and logging back in — session recovery works for 100% of active sessions.
- **SC-007**: The number of support requests related to "Excel upload failed" decreases by at least 80% compared to the current all-or-nothing approach.
- **SC-008**: Users spend less than half the time correcting invoice data compared to the current download-edit-reupload cycle.

## Assumptions

1. **Single active session**: Only one staging session per user is needed. If a user uploads a new file while one is in progress, the old one is automatically replaced.
2. **No collaborative editing**: Only the user who uploaded the file can view and edit the staging session. No multi-user collaboration.
3. **Inline editing is sufficient**: A simple inline input/select is adequate for cell editing. We are not building a full spreadsheet with formulas, copy-paste ranges, or undo/redo.
4. **Recheck validates all edited rows**: The "Recheck" re-validates all rows that have been edited since the last recheck or initial parse, not just errored rows. This catches errors accidentally introduced on previously valid rows.
5. **Partial commit**: If some invoices fail at commit time (e.g., duplicate invoice numbers), the successful ones are still created. Failed ones are reported to the user.
6. **Session expiry**: 7 days is a reasonable default for abandoned staging sessions.
7. **The existing Excel template format (16 columns) remains unchanged** — only the upload workflow changes.
8. **Rate limiting**: The existing rate limit (5 uploads per hour) applies to the staging upload endpoint as well.
