# Feature Specification: Non-blocking Bulk Invoice Operations

**Feature Branch**: `004-async-bulk-operations`  
**Created**: 2026-07-25  
**Status**: Draft  
**Input**: User request to handle the blocking issue on `/invoices/history` where bulk validation and bulk posting operations lock the user's browser until completion, and all processing is lost if the user navigates away or reloads the page.

## Clarifications

### Session 2026-07-25

- Q: How should the system handle a background bulk operation that crashes partway through (unhandled exception)? → A: Mark the task as "failed" with an error message; any already-processed invoices keep their new status; user sees the failure and can restart for remaining invoices.
- Q: Should progress be visible only on the history page or globally across the application? → A: Progress visible only on the history page; a completion/failure toast notification appears on whatever page the user is currently viewing when the operation finishes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start Bulk Validation and Continue Working (Priority: P1)

An accountant selects 20 draft invoices on the invoice history page and clicks "Validate." Instead of being stuck watching a spinner for several minutes while each invoice is validated against FBR one by one, the user sees a confirmation that validation has started and can immediately continue browsing, filtering, or working on other invoices. A progress indicator shows how many invoices have been processed so far, updating in real time. The validation continues in the background even if the user navigates to a different page within the application.

**Why this priority**: This is the core blocking issue the user reported. Bulk validation is the most painful operation because it loops through invoices one-by-one in the browser, making the user completely stuck. Solving this delivers immediate relief.

**Independent Test**: Select 5 draft invoices on the invoice history page, click Validate, verify the UI is immediately responsive (buttons clickable, navigation possible), and verify progress updates appear showing invoices being validated one by one. Navigate to another page and return — verify progress is still visible and updating.

**Acceptance Scenarios**:

1. **Given** a user has selected 10 draft invoices, **When** they click "Validate Selected," **Then** they receive an immediate confirmation message, the UI becomes responsive again, and a progress indicator appears showing "0 of 10 processed."
2. **Given** a bulk validation is in progress (5 of 10 done), **When** the user navigates to the dashboard and returns to the history page, **Then** the progress indicator still shows the operation is running and updates with the current count.
3. **Given** a bulk validation is in progress, **When** validation of invoice #3 fails with an FBR error, **Then** the progress continues to invoice #4, the failure count increments, and the specific error is recorded for later review.
4. **Given** a bulk validation has finished (8 success, 2 failed), **When** the final invoice is processed, **Then** the user sees a completion notification with the summary (8 validated, 2 failed), the invoice list refreshes to reflect updated statuses, and the error details for the 2 failures are available for review.

---

### User Story 2 - Start Bulk Posting Without Waiting (Priority: P1)

An accountant selects 15 validated invoices and clicks "Post to FBR." Instead of watching a single spinner for the entire duration (which can take several minutes as each invoice is posted sequentially to FBR), the user receives immediate confirmation that posting has started and can continue working. Progress is shown in real time. The posting continues server-side regardless of whether the user stays on the page or navigates away.

**Why this priority**: Equal priority to validation — this is the second half of the reported blocking problem. Bulk posting contacts FBR for every invoice and is equally slow. Users must not be locked out of the application during this process.

**Independent Test**: Select 3 validated invoices, click Post, verify immediate UI responsiveness, verify progress updates, verify the invoice list updates when posting completes.

**Acceptance Scenarios**:

1. **Given** a user has selected 5 validated invoices, **When** they click "Post to FBR," **Then** they receive an immediate confirmation, the UI is responsive, and a progress indicator shows "0 of 5 posted."
2. **Given** a bulk posting operation is running, **When** the user closes the browser tab and reopens the application, **Then** the operation is still processing server-side and the progress is recovered when they return to the history page.
3. **Given** a bulk posting operation completes with 4 successes and 1 failure, **When** the user views the results, **Then** they see which invoice failed and the specific FBR error message, and the 4 successfully posted invoices now show "POSTED" status.

---

### User Story 3 - View and Recover In-Progress Operations (Priority: P2)

A user who started a bulk validation or posting operation and then navigated away (or accidentally closed the tab) wants to check the status of their operation. When they return to the invoice history page, any active background operations are automatically detected and their progress is displayed. Completed operations show their final results. The user can dismiss results they've already reviewed.

**Why this priority**: Enables the "fire and forget" pattern to actually work. Without recovery, users who navigate away would never know if their operation succeeded or failed.

**Independent Test**: Start a bulk validate with 10 invoices, immediately navigate to dashboard, then return to history page — verify the progress card is still visible and updating. Close the browser tab, reopen, log back in, go to history page — verify the completed operation's results are shown.

**Acceptance Scenarios**:

1. **Given** a bulk operation is in progress server-side, **When** the user navigates to the history page (from any other page), **Then** the in-progress operation and its current progress are automatically displayed.
2. **Given** a bulk operation completed while the user was on a different page, **When** the user returns to the history page, **Then** a completion summary is shown with success/failure counts and any error details.
3. **Given** a user has reviewed a completed operation's results, **When** they dismiss the result card, **Then** the card is removed from view and does not reappear.

---

### User Story 4 - Concurrent Operation Protection (Priority: P3)

The system prevents a user from starting a second bulk operation (validate or post) while one is already in progress, to avoid conflicting FBR submissions and database inconsistencies. The user is informed with a clear message if they attempt to start a new operation while another is running.

**Why this priority**: Important for data integrity but less critical than the core non-blocking functionality. Most users will not attempt concurrent operations, but the system must guard against it.

**Independent Test**: Start a bulk validate with 20 invoices, then immediately try to start a bulk post — verify a message appears saying an operation is already in progress.

**Acceptance Scenarios**:

1. **Given** a bulk validation is currently in progress, **When** the user selects different invoices and clicks "Post to FBR," **Then** they see a message: "A validation operation is already in progress. Please wait for it to complete."
2. **Given** a bulk posting is in progress, **When** the user selects invoices and clicks "Validate Selected," **Then** they see a similar blocking message.
3. **Given** a bulk operation completed 30 seconds ago, **When** the user starts a new operation, **Then** the new operation is accepted because the previous one has finished.

---

### Edge Cases

- What happens if the server restarts while a background operation is mid-way? In-progress operations are lost (same as the existing Excel upload background validation). The auto-posting scheduler (which runs every 5 minutes) will naturally pick up validated-but-unposted invoices. Any invoices not yet validated will remain in their pre-operation state and the user can re-initiate validation.
- What happens if a single invoice in the batch has been deleted by another user/session mid-operation? The background processor skips it, records a "not found" error, and continues with the next invoice.
- What happens if the FBR gateway is unreachable for one invoice? That invoice is marked failed with the error reason, and the operation continues to the next invoice. The entire batch is not blocked by one failure.
- What happens if the user logs out while an operation is in progress? The operation continues server-side. When they log back in, the operation is recovered and displayed.
- What happens with very large selections (50+ invoices)? The operation processes sequentially, same as it does now, but without blocking the UI. A progress bar with count makes the wait tolerable.
- What happens to completed operation data over time? Completed operation records are automatically cleaned up after a reasonable period (5-10 minutes), preventing database accumulation.
- What happens if the background processing task itself crashes (e.g., database connection loss, memory error)? The task is marked as "failed" with an error description. Any invoices that were already successfully processed before the crash retain their updated status. The user sees the failure notification with details of which invoices were processed and which remain, and can re-initiate the operation for the remaining invoices.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to initiate bulk validation of selected invoices and immediately return control of the UI to the user while processing continues server-side.
- **FR-002**: System MUST allow users to initiate bulk posting of selected invoices and immediately return control of the UI to the user while processing continues server-side.
- **FR-003**: System MUST display real-time progress for in-progress bulk operations on the invoice history page, including: number of invoices processed out of total, number of successes, number of failures, and an overall percentage bar.
- **FR-004**: System MUST persist in-progress operation state so it can be recovered when the user navigates to a different page and returns, or closes and reopens the application.
- **FR-005**: System MUST continue background processing even when the user navigates away from the invoice history page.
- **FR-006**: System MUST notify the user via a toast notification when a background operation completes or fails, shown on whichever page the user is currently viewing, with a summary of successes and failures and per-failure error details available on the history page.
- **FR-007**: System MUST prevent a user from starting a new bulk operation (validate or post) while another bulk operation is still in progress for that user.
- **FR-008**: System MUST allow the user to dismiss completed operation results from their view without affecting the operation's outcome or the invoice data.
- **FR-009**: Each individual invoice failure within a bulk operation MUST NOT stop the processing of remaining invoices in the batch.
- **FR-010**: If the background processing task itself encounters a fatal error (crash), the system MUST mark the task as "failed," preserve the status of any already-processed invoices, and provide the user with enough detail to re-initiate the operation for the remaining unprocessed invoices.
- **FR-011**: System MUST automatically clean up completed operation records after a reasonable window (no more than 10 minutes) to prevent database accumulation.
- **FR-012**: Existing single-invoice validate and post operations (row-level buttons) MUST continue to work unchanged as they do today.
- **FR-013**: Existing invoice data, existing API endpoints, and existing database tables MUST NOT be modified or affected — all new functionality is additive.

### Key Entities *(include if feature involves data)*

- **Bulk Operation Task**: A temporary record representing a single bulk operation (validate or post). It tracks: which invoices are in the batch, the operation type (validate or post), current processing progress (processed/total/success/failure counts), per-invoice error details, when it started, and when it completed. This record is transient — it exists only during processing and for a short window after completion, then is automatically deleted.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users regain full control of the application UI within 2 seconds of clicking "Validate Selected" or "Post to FBR," regardless of how many invoices are selected.
- **SC-002**: Progress updates for in-progress operations appear at least every 5 seconds, showing the current processed count and success/failure breakdown.
- **SC-003**: An in-progress operation survives page navigation — when a user navigates away and returns, the operation's current progress is displayed within 3 seconds of arriving on the history page.
- **SC-004**: Users can successfully complete other invoice operations (view, filter, search, single-invoice actions) while a bulk operation is running in the background.
- **SC-005**: 100% of bulk operation results are preserved even if the user closes their browser mid-operation — when they log back in and visit the history page, the completed result is shown.
- **SC-006**: Completed operation records are deleted from the system within 10 minutes of completion, preventing any long-term storage of temporary operation data.
