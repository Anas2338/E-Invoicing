# Feature Specification: Digital FTE Invoice Automation

**Feature Branch**: `001-invoice-automation`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: User description: "Add an autonomous automation layer to the existing manual invoice portal that allows users to schedule bulk invoice submissions to FBR via Excel upload"

## Clarifications

### Session 2026-04-04

- Q: How should the system handle duplicate invoice numbers within a single uploaded Excel file? → A: Reject entire upload - show error listing duplicate invoice numbers, require user to fix and re-upload
- Q: How should the system handle invoices with scheduled times that are already in the past when the Excel file is uploaded? → A: Accept but skip - store the invoices but mark them as "expired" and never process them
- Q: How should the system handle invoices when the FBR portal is down or unreachable during the scheduled processing time? → A: Mark as failed with retry flag - update status to "failed" with reason "FBR unreachable", but allow manual retry from dashboard

### Session 2026-04-06

- **Architecture Change**: Excel files should be parsed in memory and data stored directly in PostgreSQL database instead of saving files to disk. This eliminates filesystem dependencies, simplifies deployment, and centralizes all data in the database. Users can export processed invoice data to Excel from the dashboard when needed
- Q: How should the system handle concurrent Excel uploads from the same user? → A: Block new upload - show error message "Previous upload still processing, please wait" until first upload completes
- Q: How should the system handle timezone for scheduled times? → A: Assume server timezone - all times in Excel are interpreted as server timezone, no conversion needed
- Q: What is the maximum number of invoice rows allowed in a single Excel upload? → A: 1,000 rows hard limit - reject uploads exceeding this limit with clear error message
- Q: How should the system handle FBR API rate limit errors during bulk invoice submission? → A: Mark as failed with reason "FBR rate limit exceeded", allow manual retry from dashboard (consistent with other failure handling)
- Q: When multiple invoices are scheduled for the same hour, in what order should they be processed? → A: Upload order (FIFO) - process invoices in the order they were uploaded (earliest upload timestamp first)

### Session 2026-04-10

- Q: How should the AI Agent and FTE worker coordinate to prevent duplicate invoice processing? → A: Deprecate FTE worker - AI Agent fully replaces it. The AI Agent provides superior capabilities (5-minute precision vs hourly, intelligent error handling, retry logic) and eliminating the FTE worker simplifies architecture and prevents coordination complexity
- Q: How does the AI Agent achieve 5-minute precision checks if Ralph Loop only runs hourly? → A: Ralph Loop runs hourly as orchestrator - AI Agent internally runs 5-minute checks between hourly triggers. Ralph Loop ensures the agent stays alive and performs health checks, while the agent handles its own fine-grained scheduling internally
- Q: What does "Agent Skills" mean in terms of implementation structure? → A: Agent Skills are Python modules/classes - modular code components that the AI Agent orchestrates and calls as functions. This provides testable, maintainable business logic that integrates with existing services while the AI Agent provides intelligent decision-making and orchestration
- Q: How should AI Agent-specific data be stored in the database? → A: Hybrid approach - Extend automation_invoice table with retry fields (retry_count, last_retry_at, priority). Store AI Agent decisions in automation_log table with decision rationale in action_details. Create new ai_agent_health_check table for health check data (separate from transactional invoice data)
- Q: How should the AI Agent be deployed and run in production? → A: Docker container - AI Agent runs in its own container, separate from backend, managed by docker-compose. This provides isolation, independent resource allocation, and simplified deployment across environments

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Excel Template Download and Upload (Priority: P1)

As an authenticated user, I want to download a pre-formatted Excel template, fill it with my sales invoice data offline, and upload it to the portal so that I can schedule bulk invoice submissions without manually entering each invoice.

**Why this priority**: This is the foundation of the automation system. Without the ability to upload bulk invoice data, no automation can occur. This delivers immediate value by allowing users to prepare invoices offline and upload them in bulk.

**Independent Test**: Can be fully tested by logging in, downloading the template, filling it with sample invoice data (including scheduled date/time), uploading the file, and verifying the system accepts and stores the data. Delivers value by eliminating repetitive manual data entry.

**Acceptance Scenarios**:

1. **Given** I am logged into the portal, **When** I navigate to the Automation section and click "Download Template", **Then** I receive an Excel file with pre-defined column headers (invoice_number, customer_name, items, amount, tax, scheduled_date, scheduled_time, status, reason)
2. **Given** I have filled the Excel template with valid invoice data, **When** I upload the file to the portal, **Then** the system parses the file in memory, validates the structure, stores all invoice data directly in the database, and displays a success message with the count of invoices uploaded
3. **Given** I upload an Excel file with invalid structure (missing required columns), **When** the system processes the file, **Then** I receive a clear error message indicating which columns are missing or incorrectly formatted
4. **Given** I have uploaded an Excel file, **When** the upload completes, **Then** all invoice data is stored in the database and the uploaded file is not saved to disk

---

### User Story 2 - Autonomous Invoice Processing (Priority: P1)

As a user who has uploaded scheduled invoices, I want the system to automatically validate and submit my invoices to FBR at the scheduled times without any manual intervention, so that I can focus on other business activities while invoices are submitted 24/7.

**Why this priority**: This is the core automation capability that defines the "Digital FTE" concept. Without autonomous processing, the system is just a bulk upload tool. This delivers the primary value proposition of hands-free invoice submission.

**Independent Test**: Can be fully tested by uploading an Excel file with invoices scheduled for the current hour, waiting for the hourly check to run, and verifying that valid invoices are submitted to FBR, the Excel file is updated with status information, and the database reflects the processing results.

**Acceptance Scenarios**:

1. **Given** I have uploaded invoices scheduled for the current hour, **When** the FTE worker runs its hourly check, **Then** the system identifies all invoices where scheduled_time matches the current hour and status is "pending"
2. **Given** the FTE worker has identified pending invoices for the current hour, **When** it processes each invoice, **Then** it validates the invoice data against FBR rules (required fields, tax calculations, format compliance)
3. **Given** an invoice passes validation, **When** the FTE worker submits it to FBR, **Then** the system receives a confirmation response from FBR, updates the invoice status to "submitted", stores the FBR response in the database, and logs the submission timestamp
4. **Given** an invoice fails validation, **When** the FTE worker processes it, **Then** the system updates the invoice status to "failed", records the specific validation errors in the database, and does not attempt FBR submission
5. **Given** an invoice submission to FBR fails due to network or API errors, **When** the error occurs, **Then** the system updates the invoice status to "failed", records the error details in the database, and logs the failure for retry consideration
6. **Given** the FTE worker has processed invoices, **When** processing completes, **Then** all invoice statuses and processing results are stored in the database and visible on the dashboard
7. **Given** the FTE worker runs every hour, **When** no invoices are scheduled for the current hour, **Then** the system completes the check without processing and logs the check completion

---

### User Story 3 - Automation Dashboard and Monitoring (Priority: P2)

As a user who has uploaded invoices for automation, I want to view a dashboard showing real-time statistics and detailed status of all my invoices (validated, submitted, pending, failed) with filtering and download capabilities, so that I can monitor automation progress and take action on failed submissions.

**Why this priority**: While not blocking the core automation functionality, visibility into automation status is critical for user confidence and troubleshooting. Users need to know what happened to their invoices without manually checking the Excel file.

**Independent Test**: Can be fully tested by uploading invoices, allowing the FTE worker to process them, then accessing the dashboard to verify statistics are accurate, filters work correctly, and the updated Excel file can be downloaded.

**Acceptance Scenarios**:

1. **Given** I have uploaded invoices and some have been processed, **When** I navigate to the Automation Dashboard, **Then** I see summary statistics showing total invoices uploaded, validated count, submitted count, failed count, and pending count
2. **Given** I am viewing the dashboard, **When** I apply filters (by status, date range), **Then** the invoice list updates to show only invoices matching the filter criteria
3. **Given** I am viewing the dashboard, **When** I click on a specific invoice, **Then** I see detailed information including invoice data, scheduled time, current status, FBR response (if submitted), validation errors (if failed), and processing timestamp. For failed invoices, I see a "Retry" button to manually resubmit
4. **Given** I have invoices that have been processed, **When** I click "Export to Excel", **Then** I receive a newly generated Excel file containing all my invoice data with current status and reason columns filled in based on processing results
5. **Given** I am viewing the dashboard, **When** the page loads, **Then** I see a list of recent submissions with timestamps, showing the most recent activity first

---

### User Story 6 - File and Invoice Management (Priority: P2)

As a user who has uploaded multiple Excel files with invoices, I want to manage my uploaded files and control which invoices are submitted to FBR, so that I can delete old uploads, remove incorrect data, and prevent specific invoices from being posted.

**Why this priority**: Users need control over their automation data. They should be able to correct mistakes by deleting entire upload sessions or blocking specific invoices from submission without losing all their work.

**Independent Test**: Can be fully tested by uploading multiple Excel files, then deleting one upload session, blocking specific invoices, and verifying the AI Agent respects these changes.

**Acceptance Scenarios**:

1. **Given** I have uploaded multiple Excel files, **When** I navigate to the Upload History section, **Then** I see a list of all my upload sessions with upload date, invoice count, and status summary (pending/submitted/failed counts)
2. **Given** I am viewing my upload history, **When** I click "Delete" on an upload session, **Then** the system prompts for confirmation and upon confirmation deletes all invoices from that session that have not yet been submitted to FBR
3. **Given** I attempt to delete an upload session, **When** some invoices from that session have already been submitted to FBR, **Then** the system prevents deletion and displays a message: "Cannot delete upload session - X invoices already submitted to FBR. You can only delete pending or failed invoices."
4. **Given** I am viewing the invoice list on the dashboard, **When** I select one or more pending invoices and click "Block from FBR", **Then** the system updates those invoices' status to "blocked" and the AI Agent will not process them
5. **Given** I have blocked invoices, **When** I view them on the dashboard, **Then** I see a "Unblock" button that allows me to change their status back to "pending" for processing
6. **Given** I am viewing an individual invoice detail, **When** the invoice status is "pending" or "failed", **Then** I see a "Delete Invoice" button that removes this single invoice from the system
7. **Given** I attempt to delete an invoice, **When** the invoice has already been submitted to FBR, **Then** the system prevents deletion and displays: "Cannot delete submitted invoice. Submitted invoices are permanent for audit purposes."
8. **Given** I have deleted an upload session or blocked invoices, **When** the AI Agent runs its processing cycle, **Then** it skips deleted and blocked invoices and only processes invoices with "pending" status

---

### User Story 4 - Integration with Existing Manual Invoice System (Priority: P3)

As a user of the existing manual invoice portal, I want the automation system to coexist seamlessly with my current manual invoice creation workflow, so that I can choose to use automation for bulk submissions while still creating individual invoices manually when needed.

**Why this priority**: This ensures the automation layer is truly non-invasive and doesn't disrupt existing workflows. Users should have the flexibility to use both systems based on their needs.

**Independent Test**: Can be fully tested by creating manual invoices through the existing system, then uploading automated invoices through the new system, and verifying both workflows function independently without interference.

**Acceptance Scenarios**:

1. **Given** I have created manual invoices using the existing portal, **When** I upload automated invoices through the Automation section, **Then** both manual and automated invoices are stored separately and do not interfere with each other
2. **Given** I am viewing the Automation Dashboard, **When** I filter by "manual" or "auto", **Then** I can distinguish between manually created invoices and automated submissions
3. **Given** I have both manual and automated invoices, **When** I download reports or view invoice history, **Then** I can see both types of invoices with clear indicators of their source (manual vs automated)

---

### User Story 5 - AI Agent for Continuous Monitoring and Intelligent Processing (Priority: P1)

As a user who uploads Excel files with scheduled invoices, I want an AI Agent powered by Claude Code to continuously monitor my uploads 24/7, intelligently validate and post invoices to FBR at the exact scheduled times, handle errors with smart retry strategies, and make autonomous decisions about processing priorities, so that my invoices are submitted with minimal manual intervention and maximum reliability.

**Why this priority**: This transforms the system from a simple hourly batch processor into an intelligent, proactive automation agent. The AI Agent provides continuous monitoring (not just hourly checks), intelligent error handling, adaptive retry strategies, and decision-making capabilities that go beyond rule-based automation. This is the core differentiator that makes the system truly autonomous.

**Independent Test**: Can be fully tested by uploading Excel files with various scheduled times, monitoring AI Agent logs to verify continuous operation, observing intelligent retry behavior for failed submissions, and confirming that the AI Agent makes appropriate decisions about processing priorities and error handling without human intervention.

**Acceptance Scenarios**:

1. **Given** the AI Agent is running, **When** I upload an Excel file with scheduled invoices, **Then** the AI Agent detects the new upload within 1 minute and logs the detection event with invoice count and scheduled time distribution
2. **Given** the AI Agent has detected pending invoices, **When** the scheduled time for an invoice arrives (within 5-minute precision), **Then** the AI Agent autonomously validates and posts the invoice to FBR without waiting for the next hourly batch
3. **Given** an invoice fails FBR validation, **When** the AI Agent processes the failure, **Then** it classifies the error type (transient vs permanent), determines if retry is appropriate, applies an intelligent backoff strategy (immediate, 15min, 1hr), and logs the decision rationale
4. **Given** multiple invoices are scheduled for the same time window, **When** the AI Agent processes them, **Then** it prioritizes based on business rules (high-value invoices first, expiring deadlines, customer priority), processes them in optimal order, and logs the prioritization decisions
5. **Given** the FBR API returns rate limit errors, **When** the AI Agent encounters this, **Then** it automatically throttles submission rate, queues remaining invoices, and reschedules them with appropriate delays to avoid further rate limiting
6. **Given** the AI Agent is running continuously, **When** each hour passes, **Then** the Ralph Loop hook triggers the agent to perform a comprehensive health check (pending invoice count, failed invoice analysis, FBR API status, database connectivity) and logs the system status
7. **Given** the AI Agent detects anomalies (sudden spike in failures, FBR API downtime, database connection issues), **When** the anomaly threshold is exceeded, **Then** the AI Agent logs a detailed alert with root cause analysis and recommended actions
8. **Given** I want to monitor AI Agent activity, **When** I access the dashboard, **Then** I see AI Agent status (running/stopped), last activity timestamp, decisions made in the last 24 hours, and a decision log showing what actions the agent took and why

---

### Edge Cases

- **Duplicate invoice numbers**: System rejects entire upload and displays error listing all duplicate invoice numbers, requiring user to fix and re-upload
- **Past scheduled times**: System accepts upload but marks invoices with past scheduled times as "expired" status and never processes them. These invoices are stored and visible in the dashboard but will not be submitted to FBR
- **FBR portal downtime**: When FBR portal is unreachable during scheduled processing, system marks affected invoices as "failed" with reason "FBR portal unreachable". Users can manually retry these invoices from the dashboard
- **Concurrent uploads**: If a user attempts to upload a new Excel file while a previous upload is still being processed, the system blocks the new upload and displays error message "Previous upload still processing, please wait" until the first upload completes
- **Timezone handling**: All scheduled times in Excel are interpreted as server timezone with no conversion. Users must enter times in server timezone
- **Maximum file size**: Excel files with more than 1,000 invoice rows are rejected with error message "File exceeds maximum limit of 1,000 rows". Users must split larger batches across multiple uploads
- **FBR API rate limits**: When FBR API rate limit is exceeded during bulk submissions, affected invoices are marked as "failed" with reason "FBR rate limit exceeded". Users can manually retry these invoices from the dashboard
- **Processing order**: When multiple invoices are scheduled for the same hour, they are processed in upload order (FIFO - first uploaded, first processed)
- **Memory constraints**: System handles memory constraints during Excel parsing by enforcing the 1,000 row limit (FR-004). If memory allocation fails during parsing, system returns clear error message and logs the failure. Covered by task T057 in implementation

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a downloadable Excel template with predefined column headers: invoice_number, customer_name, items, amount, tax, scheduled_date, scheduled_time, status, reason
- **FR-002**: System MUST validate uploaded Excel files in memory for correct structure (all required columns present and correctly named) and uniqueness of invoice numbers before accepting the upload. If duplicate invoice numbers are found, the system MUST reject the entire upload and display an error message listing all duplicate invoice numbers. System MUST prevent concurrent uploads from the same user by checking for in-progress uploads and displaying error message "Previous upload still processing, please wait" if an upload is already being processed. System MUST reject Excel files with more than 1,000 invoice rows with error message "File exceeds maximum limit of 1,000 rows"
- **FR-003**: System MUST parse uploaded Excel files in memory and store each row as a separate invoice record directly in the PostgreSQL database. Invoices with scheduled times in the past MUST be marked with "expired" status and excluded from FTE worker processing. The uploaded Excel file MUST NOT be saved to disk
- **FR-004**: System MUST handle memory constraints when parsing Excel files by rejecting files exceeding 1,000 rows and providing clear error messages if memory allocation fails during parsing
- **FR-005**: System MUST run an FTE worker (autonomous background process) that checks for pending invoices every hour
- **FR-006**: FTE worker MUST query for invoices where status is "pending", scheduled_date is current date, and scheduled_time hour matches current hour. Invoices with "expired" status MUST be excluded from processing. When multiple invoices match the criteria, they MUST be processed in upload order (earliest upload timestamp first)
- **FR-007**: FTE worker MUST validate each identified invoice against FBR rules including: required fields presence, tax calculation accuracy, amount format, customer information completeness
- **FR-008**: FTE worker MUST submit validated invoices to FBR portal API with proper authentication and required payload structure
- **FR-009**: System MUST update invoice status to "submitted" and store FBR response data when submission succeeds
- **FR-010**: System MUST update invoice status to "failed" and record specific error reasons in the database when validation fails or FBR submission fails
- **FR-011**: System MUST store all invoice processing results (status, validation errors, FBR responses) directly in the PostgreSQL database for real-time dashboard access
- **FR-012**: System MUST log all automation activities (validation attempts, FBR submissions, status updates) with timestamps and details for audit purposes
- **FR-013**: System MUST provide a dashboard endpoint that returns statistics: total_invoices, validated_count, submitted_count, failed_count, pending_count, expired_count
- **FR-014**: Dashboard MUST display a filterable table of invoices with columns: invoice_number, customer_name, amount, scheduled_time, status, reason, processed_at
- **FR-015**: Dashboard MUST support filtering by status (pending/expired/validated/submitted/failed) and date range
- **FR-016**: Dashboard MUST provide an export button that generates a new Excel file from database data with current status and reason information, and MUST provide a manual retry action for invoices with "failed" status
- **FR-017**: System MUST use existing Better Auth JWT-based authentication system to secure all automation features. AI Agent container MUST authenticate database access using DATABASE_URL connection string with embedded credentials, inheriting user_id context from backend API calls. No direct JWT verification required in AI Agent as it operates as a trusted backend service with database-level access control
- **FR-018**: System MUST store automation data separately without modifying existing invoice storage
- **FR-019**: System MUST handle FBR API failures (network errors, timeouts, service unavailable, rate limit exceeded) by marking invoices as "failed" with specific error reason (e.g., "FBR portal unreachable", "FBR rate limit exceeded"). Failed invoices MUST be retryable manually from the dashboard (no automatic retries in initial version)
- **FR-020**: System MUST associate all uploaded invoice data and automation records with the authenticated user's ID for data isolation

### File and Invoice Management Requirements

- **FR-034**: System MUST provide an upload history view showing all Excel upload sessions for the authenticated user with: upload timestamp, total invoice count, pending count, submitted count, failed count, blocked count
- **FR-035**: System MUST allow users to delete entire upload sessions. When deleting an upload session, the system MUST check if any invoices from that session have status "submitted". If any submitted invoices exist, deletion MUST be blocked with error message "Cannot delete upload session - X invoices already submitted to FBR. You can only delete pending or failed invoices." If no submitted invoices exist, all invoices from that session MUST be permanently deleted from the database
- **FR-036**: System MUST allow users to block individual invoices from FBR submission. When an invoice is blocked, its status MUST be updated to "blocked" and the AI Agent MUST skip it during processing. Blocked invoices can be unblocked by changing status back to "pending"
- **FR-037**: System MUST allow users to delete individual invoices. Deletion is only permitted for invoices with status "pending", "failed", "expired", or "blocked". Invoices with status "submitted" or "validated" MUST NOT be deletable, returning error "Cannot delete submitted invoice. Submitted invoices are permanent for audit purposes."
- **FR-038**: AI Agent MUST exclude invoices with status "blocked" or "deleted" from processing queries. Only invoices with status "pending" are eligible for processing
- **FR-039**: System MUST log all file management actions (upload session deletion, invoice blocking/unblocking, invoice deletion) to automation_log table with action type, affected invoice IDs, and user ID for audit trail
- **FR-040**: Dashboard statistics MUST include "blocked" count alongside existing status counts (pending, expired, validated, submitted, failed)

### AI Agent Requirements

- **FR-021**: System MUST run an AI Agent powered by Claude Code that operates continuously 24/7 as a Docker container. Ralph Loop hook triggers the agent hourly to perform health checks and ensure the agent process remains active. Between hourly triggers, the AI Agent maintains its own internal monitoring loop for fine-grained invoice processing. The agent container is managed via docker-compose alongside the backend service
- **FR-022**: AI Agent MUST implement all automation logic as modular Agent Skills (Python modules/classes) including: excel-monitor (detect new uploads), invoice-validator (validate invoice data), fbr-poster (submit to FBR), error-handler (classify and handle failures), retry-manager (intelligent retry strategies), priority-scheduler (prioritize invoice processing). The AI Agent orchestrates these skills, making intelligent decisions about when and how to invoke them
- **FR-023**: AI Agent MUST monitor the automation_invoice table continuously and detect new Excel uploads within 1 minute of upload completion
- **FR-024**: AI Agent MUST process invoices at their exact scheduled times with 5-minute precision (not just hourly batches). The agent maintains an internal monitoring loop that checks every 5 minutes for invoices due for processing, independent of the hourly Ralph Loop trigger
- **FR-025**: AI Agent MUST classify errors into categories (transient network errors, permanent validation errors, FBR API errors, rate limit errors) and apply appropriate handling strategies for each category
- **FR-026**: AI Agent MUST implement intelligent retry logic with exponential backoff: immediate retry (5 seconds) for transient errors, 15-minute delay for rate limits, 1-hour delay for FBR downtime, no retry for permanent validation errors. Retry delays use exponential backoff with jitter: base_delay * (2 ^ retry_count) + random(0, 60) seconds
- **FR-027**: AI Agent MUST prioritize invoice processing based on configurable business rules stored in ai-agent/config.py: scheduled time proximity (invoices due sooner processed first), invoice value (high-value invoices prioritized when amount > threshold), retry count (failed invoices with fewer retries prioritized), customer priority flags (if present in invoice_data). Priority score calculated as: (time_urgency_weight * time_score) + (value_weight * value_score) + (retry_weight * retry_score). Configuration MUST allow adjusting weights and thresholds without code changes
- **FR-028**: AI Agent MUST log all decisions with rationale to automation_log table using standardized schema in details JSON field: {"decision_type": "error_classification|retry_strategy|prioritization", "input_context": {"invoice_id": "uuid", "error_message": "...", "retry_history": [...]}, "ai_decision": {"classification": "TRANSIENT|PERMANENT", "recommended_action": "retry_with_backoff|skip|prioritize", "confidence": 0.0-1.0, "parameters": {}}, "rationale": "human-readable explanation", "model_used": "claude-sonnet-4-6", "timestamp": "ISO8601"}. All decision logs MUST include why an invoice was prioritized, why a retry strategy was chosen, why an error was classified as transient vs permanent, and what actions were taken
- **FR-029**: AI Agent MUST perform health checks every hour including: count of pending invoices, analysis of failed invoices (failure patterns, common errors), FBR API connectivity test, database connection verification, system resource usage
- **FR-030**: AI Agent MUST detect anomalies and log alerts when: failure rate exceeds 20% in any 1-hour rolling window (calculated as failed_count / total_processed over last 60 minutes), FBR API is unreachable for 3 consecutive health checks (15-minute window), pending invoice backlog exceeds 500 invoices at any point in time, database query latency exceeds 5 seconds for any single query. Anomaly detection runs during hourly health checks and logs alerts to ai_agent_health_check.anomalies_detected array with severity level (warning|critical) and recommended actions
- **FR-031**: AI Agent MUST expose status information via dashboard API including: agent running status, last activity timestamp, decisions made in last 24 hours, current processing queue, error classification statistics
- **FR-032**: AI Agent MUST replace the existing FTE worker as the sole invoice processor. The FTE worker (APScheduler-based hourly batch processor) will be deprecated in favor of the AI Agent's superior capabilities (5-minute precision, intelligent error handling, adaptive retry logic)
- **FR-033**: AI Agent MUST use existing FBRClient, ValidationService, and core business logic without modification, acting as an orchestration layer. Database schema changes are limited to: extending automation_invoice table with retry tracking fields (retry_count, last_retry_at, priority), using automation_log for AI decisions, and creating a new ai_agent_health_check table for operational monitoring

### Key Entities

- **Automated Invoice**: Represents a single invoice from an uploaded Excel file. Contains invoice details (number, customer, items, amounts, tax), scheduling information (date and time), processing status (pending, expired, validated, submitted, failed, blocked), validation errors if any, FBR submission response, AI Agent retry tracking (retry_count, last_retry_at), priority level for processing, and timestamps for creation and processing. Status "blocked" indicates user has prevented this invoice from being submitted to FBR. All data is stored in PostgreSQL automation_invoice table
- **Automation Activity Log**: Represents an audit trail entry tracking what happened during automation. Records the action performed (validation, submission, status update), whether it succeeded or failed, relevant details about the action, AI Agent decision rationale (stored in action_details JSON field), and when it occurred. Each log entry is associated with a specific automated invoice. Stored in automation_log table
- **Excel Upload Session**: Represents metadata about an Excel file upload. Tracks when the upload occurred, how many invoice rows were parsed, and how many have been processed. Each upload session contains multiple automated invoices. The original Excel file is not stored; only the parsed data is retained in the database. Stored in excel_upload_session table
- **AI Agent Decision**: Represents a decision made by the AI Agent during invoice processing. Contains decision type (prioritization, retry strategy, error classification), decision rationale (why this decision was made), input factors considered (invoice data, error history, system state), output action taken, confidence score, and timestamp. Stored as entries in automation_log table with action_details containing decision metadata. Used for audit trail and continuous improvement of agent logic
- **AI Agent Health Check**: Represents a periodic health check performed by the AI Agent. Contains check timestamp, pending invoice count, failed invoice analysis (failure patterns, common errors), FBR API status, database connectivity status, system resource metrics, anomalies detected, and recommended actions. Generated every hour by Ralph Loop hook. Stored in dedicated ai_agent_health_check table

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can download the Excel template and upload a filled file with 100 invoice rows in under 3 minutes
- **SC-002**: FTE worker successfully identifies and processes all invoices scheduled for the current hour within 5 minutes of the hourly check
- **SC-003**: 95% of valid invoices are successfully submitted to FBR on the first attempt (excluding FBR API downtime)
- **SC-004**: All invoice processing results are stored in the database and visible on the dashboard within 10 seconds of processing completion
- **SC-005**: Dashboard loads and displays statistics for up to 10,000 invoices in under 2 seconds
- **SC-006**: Users can filter and view invoice details on the dashboard without any errors or performance degradation
- **SC-007**: System maintains 100% data isolation between users (no user can see or access another user's automation data)
- **SC-008**: All automation activities are logged with complete audit trail (100% of actions have corresponding log entries)
- **SC-018**: Users can delete upload sessions with only pending/failed invoices in under 5 seconds
- **SC-019**: Users can block/unblock individual invoices with status update reflected in dashboard within 2 seconds
- **SC-020**: AI Agent respects blocked status and never processes blocked invoices (0% blocked invoice processing rate)
- **SC-009**: Existing manual invoice creation workflow continues to function without any disruption or performance impact
- **SC-010**: System handles Excel files with up to 1,000 invoice rows without memory errors or timeouts during in-memory parsing
- **SC-011**: AI Agent detects new Excel uploads within 1 minute of upload completion 95% of the time
- **SC-012**: AI Agent processes invoices within 5 minutes of their scheduled time 90% of the time (excluding FBR API downtime)
- **SC-013**: AI Agent correctly classifies error types with 95% accuracy (transient vs permanent errors). Measurement: Manual validation of 100 random error classifications per week during first month, comparing AI classification against expert human classification. Accuracy = (correct_classifications / total_classifications) * 100. Target: ≥95% agreement with human expert
- **SC-014**: AI Agent's intelligent retry logic reduces manual intervention by 70% compared to no-retry baseline
- **SC-015**: AI Agent logs all decisions with complete rationale (100% of processing actions have decision logs)
- **SC-016**: AI Agent health checks complete within 30 seconds and detect anomalies with 90% accuracy. Measurement: Health check duration logged in ai_agent_health_check.agent_uptime_seconds. Anomaly detection accuracy measured by comparing detected anomalies against known system issues (e.g., intentional FBR API downtime, simulated database latency). Accuracy = (true_positives + true_negatives) / (total_anomaly_scenarios) * 100. Target: ≥90% detection rate with <10% false positives
- **SC-017**: AI Agent and FTE worker operate without conflicts (0% duplicate processing of same invoice)

### Assumptions

- FBR portal provides a programmatic API for invoice submission (not just a web form)
- FBR API authentication mechanism is available and documented (API key, OAuth, or session-based)
- Server running the FTE worker has reliable internet connectivity and runs 24/7
- Excel files follow standard .xlsx format (not .xls or other formats)
- All scheduled times in Excel are in server timezone (no timezone conversion performed)
- Server has sufficient memory to parse Excel files with up to 1,000 rows in memory
- FBR API has reasonable rate limits that accommodate hourly bulk submissions
- Invoice validation rules are consistent with FBR's published requirements
- PostgreSQL database has sufficient storage capacity for invoice data and audit logs
- Claude Code API is available and accessible from the server running the AI Agent
- Ralph Loop hook can be configured to run the AI Agent every hour without conflicts
- Docker and docker-compose are available in the deployment environment
- AI Agent container has network access to PostgreSQL database and FBR API
- AI Agent has appropriate permissions to read/write automation_invoice and automation_log tables

### Out of Scope

- Real-time invoice processing (system checks hourly, not continuously)
- Automatic retry logic for failed submissions (manual resubmission required)
- Email notifications for processing completion or failures
- Multi-language support for dashboard and error messages
- Invoice editing after upload (users must upload a new Excel file)
- Integration with accounting software or ERP systems
- Mobile app for dashboard access
- Advanced scheduling (recurring invoices, conditional submission)
- Bulk deletion of submitted invoices (only pending/failed/blocked invoices can be deleted)
- Storing uploaded Excel files on disk (files are parsed in memory only)
- Version history or audit trail of Excel file uploads (only parsed invoice data is retained)
- Machine learning models for predictive failure analysis (AI Agent uses rule-based decision logic)
- Natural language interface for querying AI Agent decisions (dashboard provides structured views only)
- Real-time notifications or alerts from AI Agent (logs are written to database, external notification systems not included)
- AI Agent training or fine-tuning based on historical data (agent uses predefined logic and skills)
- Multi-agent coordination (single AI Agent instance per deployment)

