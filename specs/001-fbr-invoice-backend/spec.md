# Feature Specification: Backend System for FBR Invoice Integration Portal

**Feature Branch**: `001-fbr-invoice-backend`
**Created**: 2026-02-22
**Status**: Draft
**Input**: User description: "Backend System for FBR Invoice Integration Portal - A secure FastAPI backend service responsible for invoice processing, FBR integration, authentication enforcement, and data persistence."

## Clarifications

### Session 2026-02-22

- Q: How does the backend authenticate with FBR APIs? → A: API Key passed in request headers (e.g., X-API-Key)
- Q: How should the system implement idempotency for invoice posting? → A: Client provides idempotency key in request header; system caches results for 24 hours
- Q: Where does the backend retrieve the user's production access flag? → A: Extracted from JWT token claim (e.g., "production_access": true)
- Q: Which HTTP status codes should trigger automatic retries? → A: Only 5xx server errors and 429 rate limit responses
- Q: How should the system prevent race conditions when concurrent requests attempt to update the same invoice? → A: Optimistic locking with version field - detect conflicts at commit time, return 409 Conflict

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and Validate Invoice in Sandbox (Priority: P1)

A registered user creates a new sale or purchase invoice, fills in all required FBR fields, and validates it against the FBR sandbox environment to ensure compliance before posting.

**Why this priority**: This is the core MVP functionality. Without the ability to create and validate invoices, no other features can function. This delivers immediate value by allowing users to verify their invoice data meets FBR requirements before submission.

**Independent Test**: Can be fully tested by creating an invoice with valid FBR fields, calling the validation endpoint, and verifying the invoice transitions to "validated" state with FBR validation response stored. Delivers value by catching compliance errors early.

**Acceptance Scenarios**:

1. **Given** a user is authenticated, **When** they submit a new invoice with all required FBR fields, **Then** the system creates the invoice in "draft" state and returns the invoice ID
2. **Given** an invoice exists in "draft" state, **When** the user requests validation against FBR sandbox, **Then** the system calls FBR validation API and stores the complete response
3. **Given** FBR validation succeeds, **When** the response is received, **Then** the invoice transitions to "validated" state and the user can view validation details
4. **Given** FBR validation fails, **When** the response is received, **Then** the invoice remains in "draft" state and the user receives structured error messages from FBR

---

### User Story 2 - Post Validated Invoice to FBR (Priority: P2)

A user with a validated invoice posts it to the FBR system (sandbox or production based on their access level) and receives an FBR reference number for tracking.

**Why this priority**: This completes the invoice submission workflow. Once validation works, posting is the natural next step to achieve the business goal of submitting invoices to FBR.

**Independent Test**: Can be tested by taking a validated invoice, calling the posting endpoint, and verifying the invoice transitions to "posted" state with FBR reference number captured. Delivers value by completing the legal requirement of invoice submission.

**Acceptance Scenarios**:

1. **Given** an invoice is in "validated" state, **When** the user requests posting to FBR, **Then** the system calls FBR posting API with the validated payload
2. **Given** FBR posting succeeds, **When** the response is received, **Then** the invoice transitions to "posted" state and stores the FBR reference number
3. **Given** FBR posting fails, **When** the response is received, **Then** the invoice transitions to "failed" state and stores the error details
4. **Given** a user has sandbox-only access, **When** they attempt to post to production, **Then** the system rejects the request with an authorization error

---

### User Story 3 - Retrieve and Review Invoice History (Priority: P3)

A user views their submitted invoices with filtering options (status, date range, type, environment) and accesses detailed information including FBR responses.

**Why this priority**: This enables users to track their submission history and troubleshoot issues. It's essential for operational use but can be added after core submission functionality works.

**Independent Test**: Can be tested by creating multiple invoices with different attributes, calling the list endpoint with various filters, and verifying only the user's own invoices are returned with correct filtering applied.

**Acceptance Scenarios**:

1. **Given** a user has submitted multiple invoices, **When** they request their invoice list, **Then** the system returns only invoices belonging to that user
2. **Given** invoices exist with different statuses, **When** the user filters by status "posted", **Then** only posted invoices are returned
3. **Given** invoices exist in both sandbox and production, **When** the user filters by environment "sandbox", **Then** only sandbox invoices are returned
4. **Given** a user requests invoice details by ID, **When** the invoice belongs to them, **Then** the system returns complete invoice data including all FBR responses
5. **Given** a user requests invoice details by ID, **When** the invoice belongs to another user, **Then** the system returns a 403 Forbidden error

---

### User Story 4 - Bulk Invoice Posting (Priority: P4)

A user posts multiple validated invoices in a single operation to efficiently submit large batches to FBR.

**Why this priority**: This improves efficiency for high-volume users but is not required for basic functionality. Can be added after single invoice posting is stable.

**Independent Test**: Can be tested by creating multiple validated invoices, calling the bulk posting endpoint, and verifying each invoice is processed with individual status tracking and partial success handling.

**Acceptance Scenarios**:

1. **Given** multiple invoices are in "validated" state, **When** the user requests bulk posting, **Then** the system processes each invoice sequentially and returns individual results
2. **Given** some invoices succeed and others fail during bulk posting, **When** processing completes, **Then** successful invoices transition to "posted" and failed invoices transition to "failed" with error details
3. **Given** a bulk posting operation is in progress, **When** one invoice fails, **Then** the system continues processing remaining invoices (no all-or-nothing transaction)

---

### User Story 5 - Access Audit Logs (Priority: P5)

A system administrator or user reviews audit logs of all FBR API interactions for compliance verification and troubleshooting.

**Why this priority**: This is essential for compliance and debugging but can be implemented after core invoice operations are working. Logs should be captured from the start, but the retrieval interface can be added later.

**Independent Test**: Can be tested by performing various FBR operations, then querying the audit log endpoint and verifying all requests/responses are captured with timestamps and user context.

**Acceptance Scenarios**:

1. **Given** FBR API calls have been made, **When** an administrator requests audit logs, **Then** the system returns all logged interactions with request payload, response, timestamp, and endpoint
2. **Given** a user requests their own audit logs, **When** the query is executed, **Then** only logs for that user's invoices are returned
3. **Given** audit logs exist for multiple environments, **When** filtering by environment "production", **Then** only production API calls are returned

---

### Edge Cases

- What happens when FBR API is unavailable or times out during validation or posting?
- How does the system handle duplicate invoice submissions (same invoice posted twice)?
- What happens when a user's JWT token expires mid-operation?
- How does the system handle invoices with fields that exceed FBR maximum lengths?
- What happens when FBR returns unexpected response formats or new error codes?
- How does the system prevent race conditions when multiple requests update the same invoice simultaneously?
- What happens when a user attempts to validate an already-posted invoice?
- How does the system handle invoices created in sandbox that a user later tries to post to production?

## Requirements *(mandatory)*

### Functional Requirements

**Authentication & Authorization**

- **FR-001**: System MUST verify JWT tokens issued by Better Auth on every API request
- **FR-002**: System MUST extract user identity (user_id) from validated JWT tokens
- **FR-002a**: System MUST extract production access flag from JWT token claim (e.g., "production_access": true)
- **FR-003**: System MUST enforce row-level data isolation ensuring users can only access their own invoices
- **FR-004**: System MUST reject all requests without valid JWT tokens with 401 Unauthorized
- **FR-005**: System MUST reject requests to production posting for users without production access flag with 403 Forbidden

**Invoice Management**

- **FR-006**: System MUST create invoices in "draft" state when first submitted
- **FR-007**: System MUST store invoice payload as structured JSON preserving all FBR fields exactly as submitted
- **FR-008**: System MUST track invoice type (sale or purchase) as specified by the user
- **FR-009**: System MUST track target environment (sandbox or production) as specified by the user
- **FR-010**: System MUST assign a unique invoice ID upon creation
- **FR-011**: System MUST prevent invoice deletion (only status transitions allowed)
- **FR-012**: System MUST validate that all invoice fields conform to FBR technical specification before accepting the invoice
- **FR-012a**: System MUST implement optimistic locking using version field on Invoice entity
- **FR-012b**: System MUST increment version field on every invoice state change
- **FR-012c**: System MUST return 409 Conflict when concurrent update attempts are detected via version mismatch

**FBR Validation**

- **FR-013**: System MUST provide an endpoint to validate invoices against FBR validation API
- **FR-013a**: System MUST authenticate with FBR APIs using API key passed in request headers (e.g., X-API-Key)
- **FR-014**: System MUST only allow validation of invoices in "draft" state
- **FR-015**: System MUST store the complete FBR validation response unmodified for audit purposes
- **FR-016**: System MUST transition invoice to "validated" state only when FBR validation returns success
- **FR-017**: System MUST keep invoice in "draft" state when FBR validation returns errors
- **FR-018**: System MUST return structured FBR error messages to the user when validation fails

**FBR Posting**

- **FR-019**: System MUST provide an endpoint to post validated invoices to FBR posting API
- **FR-020**: System MUST only allow posting of invoices in "validated" state
- **FR-021**: System MUST capture and store FBR reference numbers when posting succeeds
- **FR-022**: System MUST store the complete FBR posting response unmodified for audit purposes
- **FR-023**: System MUST transition invoice to "posted" state when FBR posting returns success
- **FR-024**: System MUST transition invoice to "failed" state when FBR posting returns errors
- **FR-025**: System MUST support bulk posting of multiple validated invoices in a single request
- **FR-026**: System MUST process bulk posting with partial success handling (continue on individual failures)
- **FR-027**: System MUST implement idempotency for posting operations using client-provided idempotency key in request header
- **FR-027a**: System MUST cache idempotency results for 24 hours to handle retries with same key
- **FR-027b**: System MUST return cached response when receiving duplicate idempotency key within cache window
- **FR-028**: System MUST retry failed FBR API calls up to 3 times with exponential backoff
- **FR-028a**: System MUST only retry on 5xx server errors and 429 rate limit responses (not 4xx client errors)
- **FR-028b**: System MUST not retry on 4xx client errors as these indicate permanent failures

**Invoice Retrieval**

- **FR-029**: System MUST provide an endpoint to list invoices with filtering by status, date range, type, and environment
- **FR-030**: System MUST provide an endpoint to retrieve detailed invoice information by ID
- **FR-031**: System MUST include all FBR response history when returning invoice details
- **FR-032**: System MUST enforce user-level filtering on all retrieval operations (users see only their own data)
- **FR-033**: System MUST support pagination for invoice list results

**Logging & Audit**

- **FR-034**: System MUST log all outbound FBR API calls with request payload, response, endpoint, timestamp, and user context
- **FR-035**: System MUST maintain immutable audit history (logs cannot be modified or deleted)
- **FR-036**: System MUST provide an endpoint to retrieve audit logs with filtering by user, environment, and date range
- **FR-037**: System MUST use structured logging format for all application logs

**PDF Data Endpoint**

- **FR-038**: System MUST provide an endpoint that returns structured invoice data suitable for PDF generation
- **FR-039**: System MUST include invoice payload, FBR responses, and metadata in PDF data response

**Error Handling**

- **FR-040**: System MUST return structured error responses with appropriate HTTP status codes
- **FR-041**: System MUST preserve original FBR error payloads in error responses
- **FR-042**: System MUST handle FBR API timeouts gracefully with appropriate error messages
- **FR-043**: System MUST validate all input data and return clear validation error messages

**Environment Separation**

- **FR-044**: System MUST maintain strict separation between sandbox and production FBR configurations
- **FR-045**: System MUST prevent accidental production posting by requiring explicit environment selection per invoice
- **FR-046**: System MUST use separate configuration variables for sandbox and production FBR endpoints and credentials

### Key Entities

- **Invoice**: Represents a sale or purchase invoice submitted by a user. Contains invoice payload (structured JSON with all FBR fields), invoice type (sale/purchase), target environment (sandbox/production), current status (draft/validated/posted/failed), version field (for optimistic locking), user ownership, creation timestamp, and last updated timestamp.

- **FBR Response**: Represents a response from FBR validation or posting API. Contains response type (validation/posting), complete response payload (unmodified JSON), FBR reference number (if posting succeeded), timestamp, and relationship to parent invoice.

- **Audit Log**: Represents a logged FBR API interaction. Contains API endpoint called, request payload, response payload, HTTP status code, timestamp, user context, environment (sandbox/production), and relationship to invoice.

- **User**: Represents an authenticated portal user (managed by Better Auth). Contains user ID (from JWT), production access flag (from JWT claim "production_access"), and timestamps. User data is not stored in backend database but extracted from JWT tokens.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create and validate an invoice in under 3 seconds under normal load
- **SC-002**: System supports at least 50 concurrent invoice submissions without performance degradation
- **SC-003**: 100% of invoice fields align exactly with FBR technical specification (field names, types, formats)
- **SC-004**: Zero invoices are posted to FBR without successful prior validation
- **SC-005**: Users can only access their own invoice data (100% data isolation enforcement)
- **SC-006**: All FBR API interactions are logged with complete request/response data (100% audit coverage)
- **SC-007**: Zero accidental production postings occur from sandbox-only users
- **SC-008**: Invoice state transitions follow the defined state machine with zero invalid transitions
- **SC-009**: Bulk invoice posting handles partial failures gracefully with per-invoice status tracking
- **SC-010**: API errors return structured responses with clear error messages in 100% of failure cases
- **SC-011**: System handles FBR API timeouts and retries without data loss or corruption
- **SC-012**: All monetary values in invoices maintain precision without rounding errors

## Assumptions

- FBR API endpoints and authentication mechanisms are documented and accessible
- FBR APIs use API key authentication passed in request headers (e.g., X-API-Key)
- Better Auth JWT tokens contain user_id claim and production_access boolean claim
- FBR validation API returns consistent response formats for success and error cases
- FBR posting API provides reference numbers in a predictable response field
- Network connectivity to FBR APIs is generally reliable with occasional timeouts expected
- Invoice payloads will not exceed reasonable size limits (e.g., 1MB per invoice)
- Retry logic with 3 attempts and exponential backoff is sufficient for transient FBR API failures (5xx and 429 responses)
- Bulk posting operations will typically contain fewer than 100 invoices per request
- PDF generation will be handled by frontend or separate service using data provided by backend
- Clients will provide idempotency keys for posting operations to enable safe retries
- Idempotency cache retention of 24 hours is sufficient for typical retry scenarios

## Dependencies

- Better Auth service must be operational for JWT token verification
- FBR sandbox and production API endpoints must be accessible
- FBR API credentials and configuration must be provided via environment variables
- Neon PostgreSQL database must be provisioned and accessible
- FBR technical specification document must be available for field validation rules

## Out of Scope

- Frontend UI implementation
- PDF rendering engine (backend only provides data)
- Admin dashboard UI for system monitoring
- Third-party analytics integration
- Multi-language support for error messages
- Invoice template management
- User registration and authentication (handled by Better Auth)
- Email notifications for invoice status changes
- Scheduled/automated invoice posting
- Invoice editing after creation (only status transitions allowed)
