# Feature Specification: Auto FBR Posting with Time-Based Controls

**Feature Branch**: `003-auto-fbr-posting`  
**Created**: 2026-05-01  
**Status**: Draft  
**Input**: User description: "Implement automatic FBR posting for validated invoices with user-configurable time windows and manual override capabilities. Users can enable auto-posting in their profile with start/end times, and the AI agent will automatically post invoices to FBR during active hours. Users retain the ability to manually post individual invoices at any time."

## Clarifications

### Session 2026-05-01

- Q: How should the system handle network failures that occur after FBR accepts an invoice but before we receive confirmation? → A: Mark invoice as failed and require manual verification and reposting
- Q: Should the system support time windows that span midnight (e.g., 10:00 PM to 2:00 AM for night operations)? → A: Yes, allow spans (10 PM - 2 AM means active from 10 PM today until 2 AM tomorrow)
- Q: When a user has a midnight-spanning window and the daily limit resets at midnight, how should the system handle the limit during the active window? → A: Wait until window ends to apply new limit (10 PM - 2 AM uses previous day's limit until 2 AM)
- Q: Should the agent post invoices to FBR API sequentially or concurrently within each user's batch? → A: Sequential (post one invoice, wait for response, then post next - safer, simpler)
- Q: When a user clicks the emergency pause button, what should happen to their auto-posting configuration? → A: Disable auto-posting entirely, requiring user to manually re-enable (safest, explicit control)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Auto-Posting Settings (Priority: P1)

A user wants to enable automatic FBR posting for their validated invoices. They navigate to their profile settings, enable the auto-posting toggle, and configure their preferred posting window (e.g., 9:00 AM to 6:00 PM) along with safety controls like daily limits and environment selection.

**Why this priority**: This is the foundational capability that enables all other auto-posting features. Without configuration, no automation can occur. This delivers immediate value by allowing users to set up their automation preferences.

**Independent Test**: Can be fully tested by navigating to profile settings, configuring auto-posting parameters, saving settings, and verifying they persist across sessions. Delivers value by giving users control over automation behavior.

**Acceptance Scenarios**:

1. **Given** a user is logged in and viewing their profile settings, **When** they enable the auto-posting toggle and set start time to 9:00 AM and end time to 6:00 PM, **Then** the settings are saved and displayed correctly
2. **Given** a user has configured auto-posting settings, **When** they log out and log back in, **Then** their auto-posting settings are preserved
3. **Given** a user is configuring auto-posting, **When** they set an invalid time range (end time before start time), **Then** they receive a validation error message
4. **Given** a user has auto-posting enabled, **When** they disable the toggle, **Then** automatic posting stops immediately for future cycles
5. **Given** a user is setting up auto-posting, **When** they select a daily limit value, **Then** the system accepts values between 1 and 1000 invoices per day

---

### User Story 2 - Automatic Invoice Posting During Active Hours (Priority: P2)

A user has configured auto-posting to run between 9:00 AM and 6:00 PM. The system automatically checks for validated invoices every 5 minutes during this window and posts them to FBR without user intervention. The user can view posting progress and results in the invoice history page.

**Why this priority**: This is the core automation feature that delivers the main value proposition - hands-free invoice posting. It builds on P1 configuration and provides the actual automation benefit.

**Independent Test**: Can be tested by configuring auto-posting settings, uploading validated invoices, waiting for the scheduled time window, and verifying invoices are automatically posted to FBR. Delivers value by eliminating manual posting work.

**Acceptance Scenarios**:

1. **Given** a user has auto-posting enabled with hours 9:00 AM - 6:00 PM and it's currently 10:00 AM, **When** the AI agent runs its 5-minute check cycle, **Then** all eligible TRANSFERRED invoices are posted to FBR
2. **Given** a user has auto-posting enabled with hours 9:00 AM - 6:00 PM and it's currently 8:00 AM, **When** the AI agent runs its check cycle, **Then** no invoices are posted for this user
3. **Given** a user has a daily limit of 100 invoices and 95 have been posted today, **When** the agent finds 10 eligible invoices, **Then** only 5 invoices are posted and the rest remain in TRANSFERRED status
4. **Given** a user has auto-posting configured for Sandbox environment, **When** invoices are posted, **Then** they are sent to FBR Sandbox API, not Production
5. **Given** an invoice posting fails with a retryable error, **When** the agent processes the failure, **Then** the invoice is scheduled for retry with exponential backoff

---

### User Story 3 - Manual Override for Individual Invoices (Priority: P3)

A user needs to post a specific invoice immediately, outside of their configured auto-posting window. They navigate to the invoice history page, select the invoice, and click "Post to FBR Now" to manually trigger posting regardless of time window or auto-posting settings.

**Why this priority**: This provides flexibility and control for urgent situations. While automation handles routine posting, users need the ability to override for time-sensitive invoices.

**Independent Test**: Can be tested by disabling auto-posting or being outside the time window, selecting an invoice, clicking manual post button, and verifying immediate posting to FBR. Delivers value by handling urgent posting needs.

**Acceptance Scenarios**:

1. **Given** a user has auto-posting disabled, **When** they select a TRANSFERRED invoice and click "Post to FBR Now", **Then** the invoice is immediately posted to FBR
2. **Given** it's outside the user's configured auto-posting hours, **When** they manually post an invoice, **Then** the posting succeeds regardless of time window
3. **Given** a user has reached their daily limit, **When** they attempt to manually post an invoice, **Then** they receive a warning but can choose to proceed and exceed the limit
4. **Given** a user manually posts an invoice, **When** the posting fails, **Then** they see an immediate error message with details
5. **Given** multiple users are posting invoices simultaneously, **When** each user manually posts, **Then** their invoices are posted independently without interference

---

### User Story 4 - Monitor Posting Status and Statistics (Priority: P4)

A user wants to track the progress and results of automatic posting. They view the invoice history page which displays real-time status indicators (active/paused/outside hours), today's posting statistics (posted count, failed count), and the next scheduled check time.

**Why this priority**: Visibility into automation status builds user confidence and enables proactive issue detection. This is important but can be added after core posting functionality works.

**Independent Test**: Can be tested by enabling auto-posting, viewing the invoice history page, and verifying all status indicators and statistics display correctly and update in real-time. Delivers value through transparency and monitoring.

**Acceptance Scenarios**:

1. **Given** a user has auto-posting enabled and it's within their time window, **When** they view the invoice history page, **Then** they see a green "Auto-posting active" status indicator
2. **Given** a user has auto-posting enabled but it's outside their time window, **When** they view the invoice history page, **Then** they see an orange "Outside active hours" status indicator
3. **Given** the agent last ran 2 minutes ago, **When** a user views the invoice history page, **Then** they see "Next check in 3 minutes"
4. **Given** 45 invoices have been posted today and 2 have failed, **When** a user views the invoice history page, **Then** they see "Posted: 45 | Failed: 2" in today's statistics
5. **Given** a user has paused auto-posting temporarily, **When** they view the invoice history page, **Then** they see a red "Paused" status indicator with resume time

---

### User Story 5 - Receive Notifications About Posting Activity (Priority: P5)

A user receives automated notifications about their posting activity in the dashboard notification center, including daily summaries (posted count, failed count), alerts when daily limits are reached, and warnings when failure rates are high. This keeps users informed without requiring constant monitoring.

**Why this priority**: Notifications provide passive awareness and alert users to issues requiring attention. This is valuable but not critical for core functionality.

**Independent Test**: Can be tested by configuring auto-posting, allowing invoices to be posted throughout the day, and verifying notifications appear in the dashboard notification center at appropriate times with correct information. Delivers value through proactive communication.

**Acceptance Scenarios**:

1. **Given** a user has auto-posting enabled, **When** the day ends at midnight, **Then** they receive a daily summary notification in their dashboard with total posted and failed counts
2. **Given** a user reaches their daily posting limit, **When** the limit is hit, **Then** they receive an immediate notification in their dashboard
3. **Given** the failure rate exceeds 20% in the last hour, **When** this threshold is crossed, **Then** the user receives a high failure rate alert notification in their dashboard
4. **Given** a user has temporarily paused auto-posting, **When** the pause period ends, **Then** they receive a notification in their dashboard that auto-posting has resumed
5. **Given** 5 consecutive invoices fail for the same error, **When** this pattern is detected, **Then** the user receives a notification in their dashboard with error details and suggested actions

---

### Edge Cases

- What happens when a user changes their time window while auto-posting is active? (System should respect new settings on next cycle)
- How does the system handle timezone changes or daylight saving time transitions? (All times stored and compared in PKT timezone)
- What happens if FBR API is completely unavailable during the posting window? (Invoices remain in TRANSFERRED status, retry on next cycle)
- How does the system handle a user who disables auto-posting while invoices are currently being posted? (Current batch completes, future cycles skip this user)
- What happens when an invoice is manually posted while the agent is also trying to post it? (First successful post wins, second attempt detects duplicate and skips)
- How does the system handle a user who sets their daily limit to 0? (Validation prevents saving, minimum limit is 1)
- What happens if a user's FBR credentials expire during auto-posting? (Posting fails with authentication error, user notified to update credentials)
- How does the system handle invoices that are in TRANSFERRED status but have invalid data? (FBR API rejects them, marked as FBR_FAILED with error details)
- What happens when the daily limit is reached mid-batch? (Agent posts up to the limit, remaining invoices wait for next day)
- How does the system handle concurrent manual posts by the same user? (Each request processed independently, FBR API handles deduplication)

## Requirements *(mandatory)*

### Functional Requirements

#### Profile Configuration
- **FR-001**: System MUST allow users to enable/disable auto-posting via a toggle control in their profile settings
- **FR-002**: System MUST allow users to configure start time for auto-posting window (24-hour format, minute precision)
- **FR-003**: System MUST allow users to configure end time for auto-posting window (24-hour format, minute precision)
- **FR-004**: System MUST support time windows that span midnight (e.g., 22:00 to 02:00 means active from 10 PM today until 2 AM tomorrow)
- **FR-005**: System MUST allow users to select FBR environment (Sandbox or Production) for auto-posting
- **FR-006**: System MUST allow users to set a daily posting limit (minimum 1, maximum 1000 invoices per day)
- **FR-007**: System MUST allow users to temporarily pause auto-posting until a specified date/time
- **FR-008**: System MUST persist all auto-posting settings across user sessions
- **FR-009**: System MUST display current auto-posting configuration in profile settings
- **FR-010**: System MUST provide default values for new users (disabled, 9:00 AM - 6:00 PM, Sandbox, 100 invoices/day)

#### AI Agent Behavior
- **FR-011**: AI agent MUST check for eligible invoices every 5 minutes on a scheduled basis
- **FR-012**: AI agent MUST filter invoices by users who have auto-posting enabled
- **FR-013**: AI agent MUST verify current time (PKT timezone) is within each user's configured time window before posting
- **FR-014**: AI agent MUST respect each user's daily posting limit and stop posting when limit is reached
- **FR-015**: AI agent MUST post invoices to the FBR environment specified in user's settings (Sandbox or Production)
- **FR-016**: AI agent MUST update invoice status to FBR_POSTING when posting begins
- **FR-017**: AI agent MUST update invoice status to FBR_POSTED when FBR API returns success
- **FR-018**: AI agent MUST update invoice status to FBR_FAILED when FBR API returns error
- **FR-019**: AI agent MUST log all posting attempts with timestamp, user, invoice, and result
- **FR-020**: AI agent MUST process invoices in order of scheduled date/time, then priority
- **FR-021**: AI agent MUST process up to 10 invoices per user per cycle to ensure fair distribution, posting them sequentially (one at a time, waiting for each response before posting the next)
- **FR-022**: AI agent MUST track daily posted count per user and reset at midnight PKT, except for midnight-spanning windows which continue using the previous day's limit until the window ends

#### Error Handling and Retry
- **FR-023**: System MUST retry failed invoices up to 3 times with exponential backoff (1 min, 5 min, 15 min)
- **FR-024**: System MUST classify FBR errors as retryable (network, timeout, rate limit) or permanent (validation, authentication)
- **FR-025**: System MUST only retry invoices with retryable errors
- **FR-026**: System MUST mark invoices as permanently failed after 3 retry attempts
- **FR-027**: System MUST store detailed error messages from FBR API for troubleshooting
- **FR-028**: System MUST automatically pause auto-posting for a user if failure rate exceeds 20% in the last hour
- **FR-029**: System MUST resume auto-posting automatically after 1 hour if failure rate drops below threshold
- **FR-030**: System MUST prevent retry loops by tracking retry count per invoice
- **FR-059**: System MUST mark invoices as FBR_FAILED when network failure occurs after posting (no confirmation received), requiring manual verification before reposting to prevent duplicates in FBR system

#### Manual Override
- **FR-031**: System MUST provide a "Post to FBR Now" button for individual invoices in TRANSFERRED status
- **FR-032**: System MUST allow manual posting regardless of auto-posting enabled/disabled state
- **FR-033**: System MUST allow manual posting regardless of current time window
- **FR-034**: System MUST warn users when manual posting would exceed daily limit but allow override
- **FR-035**: System MUST post manually triggered invoices to the user's configured FBR environment
- **FR-036**: System MUST provide immediate feedback (success/error) for manual posting attempts
- **FR-037**: System MUST prevent duplicate posting if invoice is already in FBR_POSTING status
- **FR-038**: System MUST count manually posted invoices toward daily limit

#### UI and Status Display
- **FR-039**: Invoice history page MUST display auto-posting status indicator (active/paused/outside hours/disabled)
- **FR-040**: Invoice history page MUST display next scheduled check time when auto-posting is active
- **FR-041**: Invoice history page MUST display today's posting statistics (posted count, failed count, remaining limit)
- **FR-042**: Invoice history page MUST provide quick link to profile settings for auto-posting configuration
- **FR-043**: Invoice history page MUST display invoice status badges (TRANSFERRED, FBR_POSTING, FBR_POSTED, FBR_FAILED)
- **FR-044**: Invoice history page MUST show error details for failed invoices on hover or click
- **FR-045**: Invoice history page MUST refresh statistics automatically every 30 seconds
- **FR-046**: System MUST display emergency pause button that immediately disables auto-posting, requiring user to manually re-enable it in profile settings

#### Notifications
- **FR-047**: System MUST post daily summary notification at midnight PKT with posted count and failed count to user's notification dashboard
- **FR-048**: System MUST post notification to dashboard when user reaches their daily posting limit
- **FR-049**: System MUST post notification to dashboard when failure rate exceeds 20% threshold
- **FR-050**: System MUST post notification to dashboard when auto-posting is automatically paused due to high failure rate
- **FR-051**: System MUST post notification to dashboard when temporary pause period ends and auto-posting resumes
- **FR-052**: System MUST include actionable information in dashboard notifications (error details, suggested fixes, links to invoice history)

#### Security and Isolation
- **FR-053**: System MUST ensure each user can only configure auto-posting for their own account
- **FR-054**: System MUST ensure each user can only view and post their own invoices
- **FR-055**: System MUST isolate Sandbox and Production environments completely (no cross-posting)
- **FR-056**: System MUST validate user's FBR credentials before allowing auto-posting to Production
- **FR-057**: System MUST log all auto-posting configuration changes for audit trail
- **FR-058**: System MUST require re-authentication when changing FBR environment from Sandbox to Production

### Key Entities

- **User Auto-Posting Configuration**: Represents a user's auto-posting preferences including enabled status, time window (start time, end time), FBR environment selection, daily posting limit, and temporary pause settings. Each user has exactly one configuration.

- **Invoice**: Represents an invoice with status tracking through the posting lifecycle. Key attributes include status (TRANSFERRED, FBR_POSTING, FBR_POSTED, FBR_FAILED), scheduled date/time, priority, FBR response data, error messages, retry count, and posting timestamps. Each invoice belongs to one user.

- **Posting Log**: Represents a record of each posting attempt including timestamp, user, invoice, action (auto/manual), result (success/failure), FBR environment used, error details, and agent cycle identifier. Used for audit trail and analytics.

- **Daily Posting Counter**: Represents the count of invoices posted for each user on a given date. Resets at midnight PKT. Used to enforce daily limits.

- **Notification**: Represents a notification posted to the user's dashboard including notification type (daily summary, limit reached, high failure rate), content, timestamp, and read status. Used for user awareness and alerts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can configure auto-posting settings in under 2 minutes from profile page
- **SC-002**: System automatically posts eligible invoices within 5 minutes of entering the configured time window
- **SC-003**: 95% of invoices are successfully posted to FBR on first attempt during normal operation
- **SC-004**: Manual posting completes within 10 seconds from button click to status update
- **SC-005**: Users receive daily summary notifications in their dashboard within 5 minutes of midnight PKT
- **SC-006**: System handles 100 concurrent users with auto-posting enabled without performance degradation
- **SC-007**: Daily posting limits are enforced with 100% accuracy (no over-posting)
- **SC-008**: Failed invoices are retried according to schedule (1 min, 5 min, 15 min) with 95% timing accuracy
- **SC-009**: Status indicators on invoice history page update within 30 seconds of actual status change
- **SC-010**: Zero invoices are posted outside of user's configured time window
- **SC-011**: System correctly handles timezone (PKT) for all time-based operations with 100% accuracy
- **SC-012**: Users can pause and resume auto-posting with changes taking effect within 5 minutes
- **SC-013**: Manual override successfully posts invoices even when auto-posting is disabled or outside time window
- **SC-014**: System scales to support 1000 users with auto-posting enabled simultaneously
- **SC-015**: Dashboard notifications are created within 5 minutes of triggering event

## Assumptions

- Users have valid FBR credentials configured in their profile before enabling auto-posting
- FBR API has rate limits that allow posting 10 invoices per user per 5-minute cycle
- Dashboard notification system is available and reliable for posting notifications
- All times are stored and compared in PKT (Pakistan Time, UTC+5) timezone
- Users understand the difference between Sandbox and Production FBR environments
- The existing AI agent infrastructure can be extended to include FBR posting logic
- Invoice validation has already occurred before invoices reach TRANSFERRED status
- Users have appropriate permissions to post invoices to FBR (not restricted by admin)
- The system has sufficient database capacity to store posting logs and counters
- Network connectivity to FBR API is generally reliable during business hours

## Out of Scope

- AI-powered error interpretation for failed invoices (may be added in future phase)
- Batch approval workflow for high-value invoices before posting
- Smart auto-posting rules based on invoice amount or customer type
- Integration with external calendar systems for time window configuration
- Multi-environment posting (posting same invoice to both Sandbox and Production)
- Rollback or void functionality for posted invoices
- Real-time FBR API status monitoring dashboard
- Custom notification preferences (frequency, channels, content)
- Invoice posting analytics and reporting dashboard
- Automatic FBR credential refresh or rotation
- Support for posting invoices in bulk via CSV upload
- Integration with accounting software for invoice synchronization
