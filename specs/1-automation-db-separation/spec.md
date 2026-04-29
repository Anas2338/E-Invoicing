# Feature Specification: Automation Database Separation

**Feature ID**: 1-automation-db-separation  
**Created**: 2026-04-24  
**Status**: Draft  
**Owner**: [To be assigned]

---

## Overview

### Problem Statement

The current system stores both manual and automated invoice data in a single database, creating tight coupling between the automation system and the main application. This architecture has several limitations:

1. **Data Isolation**: Automation data (bulk uploads, scheduled invoices) is mixed with manual invoice data, making it difficult to manage, monitor, and scale independently
2. **User Control**: Users cannot easily review and approve automated invoices before they are posted to FBR - the AI agent posts directly without user intervention
3. **Data Retention**: Automation data accumulates indefinitely with no cleanup mechanism, leading to database bloat
4. **System Independence**: The automation system cannot be scaled, maintained, or backed up independently from the main application

### Proposed Solution

Separate the automation system into its own isolated database with a daily data transfer mechanism. The AI agent will transfer validated invoices to the main database at a scheduled time (7 PM daily), where users can review and manually post them to FBR. This gives users full control over when invoices are submitted while maintaining the convenience of bulk upload and validation.

### User Value

- **Control**: Users can review all automated invoices before posting to FBR, reducing errors and ensuring accuracy
- **Transparency**: Clear separation between automated and manual workflows makes it easier to track invoice sources
- **Data Management**: Automatic cleanup of old automation data prevents database bloat
- **Reliability**: Isolated databases reduce the risk of automation issues affecting the main application

---

## Clarifications

### Session 2026-04-24

- Q: Should transferred invoices have status "draft" (requiring user review) or "validated" (ready to post immediately)? → A: Validated status - invoices are ready to post immediately after transfer
- Q: When should FBR validation occur? → A: During Excel upload (current behavior) - validates early, catches errors immediately, AI agent only transfers pre-validated invoices

---

## User Scenarios

### Primary Scenario: Bulk Invoice Upload and Manual Posting

**Actor**: Business User (with automation access enabled)

**Flow**:
1. User uploads Excel file with 10 invoices scheduled for 2026-04-24
2. System validates invoices and stores them in the automation database
3. At 7:00 PM on 2026-04-24, the AI agent transfers all 10 validated invoices to the main database
4. User logs in and navigates to invoice history
5. User sees the 10 transferred invoices listed as manual invoices
6. User reviews each invoice and manually posts them to FBR one by one (or in batch)
7. After 2 days (2026-04-26), the automation database automatically deletes the original automation data

**Expected Outcome**: User has full control over when invoices are posted to FBR, with the convenience of bulk upload and validation

### Secondary Scenario: Failed Transfer Recovery

**Actor**: System Administrator

**Flow**:
1. Daily transfer job runs at 7:00 PM but fails due to database connectivity issue
2. System logs the failure with detailed error information
3. Administrator receives alert about failed transfer
4. Administrator investigates and resolves the connectivity issue
5. Administrator manually triggers the transfer job
6. Invoices are successfully transferred to main database
7. Users can now see and post the invoices

**Expected Outcome**: Failed transfers are detected, logged, and can be recovered without data loss

### Tertiary Scenario: User Reviews Transferred Invoice Before Posting

**Actor**: Business User

**Flow**:
1. User receives notification that 10 invoices have been transferred from automation
2. User navigates to invoice history and filters by source or date
3. User opens one invoice to review details
4. User notices an error in the invoice data
5. User edits the invoice to correct the error
6. User saves the corrected invoice
7. User posts the corrected invoice to FBR

**Expected Outcome**: Users can edit transferred invoices before posting, ensuring data accuracy

---

## Functional Requirements

### FR-1: Database Separation

**Requirement**: The system shall maintain two separate databases - a main database for manual invoices and user data, and an automation database for bulk upload and scheduled invoice data.

**Acceptance Criteria**:
- Automation database stores: automation invoices, upload sessions, automation logs
- Main database stores: manual invoices, user accounts, FBR master data
- User authentication and authorization data remains in main database
- Both databases can be backed up, scaled, and maintained independently

### FR-2: Daily Invoice Transfer

**Requirement**: The system shall automatically transfer validated invoices from the automation database to the main database at 7:00 PM daily (Pakistan Time).

**Acceptance Criteria**:
- Transfer job runs at 7:00 PM PKT every day (±5 minutes acceptable due to scheduler precision)
- Only invoices with "validated" status are transferred
- Invoices scheduled for current date or earlier are included in transfer
- Each invoice is transformed from automation format to manual invoice format
- Transferred invoices appear in user's manual invoice history
- Transfer is atomic per invoice (either fully transferred or not at all)
- Failed transfers are logged with detailed error information
- Transfer job can be manually triggered by administrators

### FR-3: Invoice Status Management

**Requirement**: The system shall assign appropriate status to transferred invoices and track their origin.

**Acceptance Criteria**:
- Transferred invoices are marked with status "validated" (ready to post immediately)
- Each invoice includes metadata indicating it was transferred from automation
- Original automation invoice is marked as "transferred" in automation database
- Transfer timestamp is recorded on both automation and manual invoice records
- Users can filter invoice history by source (manual vs automation)

### FR-4: Manual Posting Control

**Requirement**: The system shall allow users to manually review and post transferred invoices to FBR, with no automatic posting by the AI agent.

**Acceptance Criteria**:
- AI agent does not interact with FBR API for posting invoices
- Users can view all transferred invoices in their invoice history
- Users can edit transferred invoices before posting
- Users can post invoices individually or in batch
- Posting to FBR requires explicit user action (button click, API call)
- Users receive confirmation before posting to FBR

### FR-5: Data Cleanup

**Requirement**: The system shall automatically delete automation data older than 2 days to prevent database bloat.

**Acceptance Criteria**:
- Cleanup job runs daily (recommended: 2:00 AM PKT)
- Deletes automation invoices older than 2 days (based on created_at timestamp)
- Deletes associated upload sessions older than 2 days
- Preserves automation logs for audit purposes (configurable retention period)
- Cleanup is logged with count of deleted records
- Cleanup does not delete invoices that failed to transfer (marked for retry)

### FR-6: User Experience Consistency

**Requirement**: The system shall provide a seamless user experience where transferred invoices behave identically to manually created invoices.

**Acceptance Criteria**:
- Transferred invoices appear in the same invoice history view as manual invoices
- Users can perform all standard operations on transferred invoices (view, edit, delete, post)
- Invoice detail view shows the same information regardless of source
- Posting workflow is identical for manual and transferred invoices
- Users can distinguish invoice source through metadata or filter

### FR-7: Error Handling and Recovery

**Requirement**: The system shall handle transfer failures gracefully and provide recovery mechanisms.

**Acceptance Criteria**:
- Transfer failures do not cause data loss in automation database
- Failed transfers are logged with timestamp, error message, and affected invoice IDs
- Administrators can view failed transfer logs
- Failed invoices remain in automation database with "transfer_failed" status
- Administrators can manually retry failed transfers
- Duplicate transfer prevention: same invoice cannot be transferred twice

---

## Success Criteria

### Measurable Outcomes

1. **User Control**: 100% of automated invoices require explicit user action before posting to FBR
2. **Data Isolation**: Automation database can be taken offline without affecting manual invoice operations
3. **Transfer Reliability**: 99.9% of scheduled transfers complete successfully within 5 minutes of scheduled time
4. **Data Cleanup**: Automation database size remains stable (no growth beyond 7 days of data)
5. **User Satisfaction**: Users can review and edit transferred invoices before posting
6. **Performance**: Transfer of 1000 invoices completes within 10 minutes
7. **Recovery Time**: Failed transfers can be recovered within 1 hour of detection

### Qualitative Outcomes

1. Users feel confident that automated invoices are accurate before posting
2. System administrators can manage automation and main databases independently
3. Users understand the difference between manual and automated invoice workflows
4. Failed transfers are detected and resolved without user impact

---

## Key Entities

### Automation Invoice (Automation Database)

**Purpose**: Stores bulk-uploaded invoices awaiting validation and transfer

**Key Attributes**:
- Unique identifier
- User identifier (reference to main database user)
- Invoice data (JSON format)
- Scheduled date and time
- Status (pending, validated, transferred, transfer_failed, expired)
- Validation errors (if any)
- FBR validation response
- Created timestamp
- Transfer timestamp
- Retry count

### Manual Invoice (Main Database)

**Purpose**: Stores user-created and transferred invoices for manual posting

**Key Attributes**:
- Unique identifier
- User identifier
- Invoice details (structured fields: seller, buyer, items, amounts)
- Status (draft, validated, posted, failed)
- Source (manual, automation)
- Transfer metadata (if from automation)
- Created timestamp
- Posted timestamp
- FBR response

### Upload Session (Automation Database)

**Purpose**: Tracks bulk Excel upload sessions

**Key Attributes**:
- Unique identifier
- User identifier
- Original filename
- Total rows
- Processed rows
- Processing status
- Created timestamp

### Transfer Log (Automation Database)

**Purpose**: Audit trail of daily transfer operations

**Key Attributes**:
- Unique identifier
- Transfer timestamp
- Status (success, partial_success, failed)
- Invoices transferred count
- Invoices failed count
- Error details
- Duration

---

## Assumptions

1. **Database Technology**: Both databases use PostgreSQL (or compatible)
2. **Network Connectivity**: Reliable network connection exists between automation and main databases
3. **Time Zone**: All scheduled times are in Pakistan Time (PKT, UTC+5)
4. **User Authentication**: Users authenticate against main database only
5. **Data Volume**: Daily transfer volume does not exceed 10,000 invoices per user
6. **Transfer Window**: 7:00 PM is an acceptable time for all users (no timezone customization needed)
7. **Edit Capability**: Users can edit transferred invoices before posting (no restrictions)
8. **Cleanup Policy**: 2-day retention is sufficient for all business needs
9. **FBR Validation**: FBR validation happens during Excel upload to catch errors early and provide immediate feedback to users. Only pre-validated invoices are transferred to the main database.
10. **Duplicate Prevention**: Invoice numbers are unique within user scope

---

## Constraints

### Business Constraints

1. **User Access**: Only users with automation access enabled can upload bulk invoices
2. **Data Retention**: Automation data must be retained for at least 2 days for audit purposes
3. **Manual Posting**: All invoices must be posted manually by users (no automatic posting)
4. **Transfer Schedule**: Transfer time (7:00 PM) is fixed and cannot be customized per user

### Technical Constraints

1. **Database Isolation**: No foreign key constraints across databases
2. **Transaction Boundaries**: Cannot guarantee atomic transactions across both databases
3. **Data Consistency**: Application-level consistency checks required
4. **Network Dependency**: Transfer requires network connectivity between databases
5. **Scheduler Dependency**: Requires APScheduler or equivalent for scheduled jobs

### Security Constraints

1. **User Isolation**: Users can only access their own invoices in both databases
2. **Admin Access**: Only administrators can trigger manual transfers or view transfer logs
3. **Data Encryption**: Database connections must use SSL/TLS
4. **Audit Trail**: All transfers and deletions must be logged

---

## Dependencies

### Internal Dependencies

1. **User Authentication System**: Must validate user identity before allowing invoice access
2. **FBR Master Data**: Required for invoice validation (stored in main database)
3. **APScheduler**: Existing scheduler infrastructure for daily jobs
4. **Database Session Management**: Must support multiple database connections

### External Dependencies

1. **Neon Database**: Separate Neon project for automation database
2. **Network Infrastructure**: Reliable connectivity between databases
3. **Monitoring System**: For alerting on transfer failures

---

## Out of Scope

The following items are explicitly **not** included in this feature:

1. **Real-time Transfer**: Transfer happens once daily, not in real-time
2. **User-Configurable Schedule**: Transfer time is fixed at 7:00 PM PKT
3. **Selective Transfer**: All validated invoices are transferred (no user selection)
4. **Cross-Database Queries**: No ability to query both databases simultaneously
5. **Automatic Posting**: AI agent will not post invoices to FBR
6. **Invoice Approval Workflow**: No multi-step approval process for transferred invoices
7. **Rollback Mechanism**: Cannot roll back transferred invoices to automation database
8. **Custom Retention Policies**: 2-day cleanup period is fixed
9. **Transfer History UI**: No user-facing interface for viewing transfer history (admin only)
10. **Partial Invoice Transfer**: Invoices are transferred in full or not at all

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-24 | AI Assistant | Initial specification |
| 1.1 | 2026-04-24 | AI Assistant | Clarifications added: invoice status (validated), FBR validation timing (during upload) |

---

## Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | | | |
| Technical Lead | | | |
| Stakeholder | | | |
