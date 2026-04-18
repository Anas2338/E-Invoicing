# Research & Architectural Decisions: User Approval System

**Feature**: 002-user-approval-system  
**Date**: 2026-04-13  
**Status**: Implemented (Retroactive Documentation)

---

## Overview

This document captures the architectural decisions made during implementation of the user approval system. Since the feature was implemented before formal planning, this serves as retroactive documentation of the design choices and their rationale.

---

## Key Architectural Decisions

### Decision 1: Extend User Model vs Separate Approval Entity

**Decision**: Extend existing User model with approval fields

**Rationale**:
- User approval is a core property of user identity, not a separate workflow entity
- Simpler data model with fewer joins required for authentication checks
- Approval status is permanent and doesn't require versioning or history tracking
- Reduces complexity in authentication middleware (single table lookup)

**Alternatives Considered**:
1. **Separate UserApproval table**: Would require joins on every authentication check, adding latency
2. **Separate PendingUser table**: Would require data migration between tables on approval, increasing complexity
3. **Event sourcing approach**: Overkill for simple status tracking, adds unnecessary complexity

**Trade-offs**:
- ✓ Simpler authentication logic
- ✓ Better query performance (no joins)
- ✓ Single source of truth for user status
- ✗ User table grows with approval metadata (acceptable given small scale)

---

### Decision 2: Status Enum vs Boolean Flags

**Decision**: Use single `account_status` field with enum values (pending, approved, rejected)

**Rationale**:
- Mutually exclusive states are better represented as enum than multiple booleans
- Prevents invalid states (e.g., both approved and rejected being true)
- Easier to extend with additional states in future (e.g., suspended, archived)
- More readable in queries and logs

**Alternatives Considered**:
1. **Boolean flags** (`is_approved`, `is_rejected`): Risk of invalid state combinations
2. **Numeric status codes**: Less readable, requires lookup table for meaning
3. **Separate approved/rejected timestamps**: Doesn't clearly indicate current state

**Trade-offs**:
- ✓ Type-safe state representation
- ✓ Prevents invalid state combinations
- ✓ Self-documenting code
- ✗ Requires database migration to add new states (acceptable given infrequent changes)

---

### Decision 3: Admin Role via approval_flags vs Roles Table

**Decision**: Use existing `approval_flags` JSON field with `is_admin` boolean

**Rationale**:
- Leverages existing flexible permissions structure
- Avoids adding new tables for simple admin/non-admin distinction
- Consistent with existing permission system (has_production_access, can_post_to_production)
- Sufficient for current requirements (no complex role hierarchy needed)

**Alternatives Considered**:
1. **Separate roles table with many-to-many**: Overkill for binary admin/user distinction
2. **Hardcoded admin user IDs**: Not scalable, requires code changes to add admins
3. **Separate is_admin boolean column**: Inconsistent with existing permission pattern

**Trade-offs**:
- ✓ Consistent with existing permission system
- ✓ No additional tables or migrations
- ✓ Flexible for future permission additions
- ✗ JSON field less type-safe than dedicated columns (mitigated by application-level validation)

---

### Decision 4: Email Notifications via Console Logging

**Decision**: Implement email notification functions that log to console with TODO comments for SMTP integration

**Rationale**:
- Allows feature to be functional without external email service dependency
- Provides clear structure for future SMTP integration
- Enables testing and development without email configuration
- Admin can manually notify users if needed during initial rollout

**Alternatives Considered**:
1. **Require SMTP configuration upfront**: Blocks feature deployment on email service availability
2. **No notification system**: Poor user experience, users don't know approval status
3. **In-app notifications only**: Requires users to be logged in to see status (they can't login when pending)

**Trade-offs**:
- ✓ Feature deployable without email service
- ✓ Clear upgrade path to real email
- ✓ Testable without external dependencies
- ✗ Manual notification required initially (acceptable for low volume)

---

### Decision 5: Auto-Approve Existing Users During Migration

**Decision**: Set all existing users to `account_status = 'approved'` during migration

**Rationale**:
- Existing users are already vetted and actively using the system
- Prevents disruption to current user workflows
- Maintains backward compatibility
- Only new registrations require approval

**Alternatives Considered**:
1. **Set existing users to pending**: Would lock out all current users, requiring mass approval
2. **Grandfather existing users with special flag**: Adds complexity without benefit
3. **Manual approval of existing users**: Unnecessary administrative burden

**Trade-offs**:
- ✓ Zero disruption to existing users
- ✓ Backward compatible
- ✓ Immediate feature activation for new users only
- ✗ No approval audit trail for existing users (acceptable given they're already trusted)

---

### Decision 6: Admin Panel as Protected Route

**Decision**: Create admin panel at `/admin/users` within existing Next.js app

**Rationale**:
- Leverages existing authentication and routing infrastructure
- Consistent with application architecture
- No separate admin application to maintain
- Uses same design system and components

**Alternatives Considered**:
1. **Separate admin application**: Adds deployment complexity, duplicates auth logic
2. **Backend-only admin CLI**: Poor UX, requires terminal access
3. **Admin functionality in main dashboard**: Clutters user interface, confusing for non-admins

**Trade-offs**:
- ✓ Single application to maintain
- ✓ Consistent UX and design
- ✓ Reuses existing auth infrastructure
- ✗ Admin routes accessible to all users (mitigated by backend authorization checks)

---

### Decision 7: Synchronous Approval Actions

**Decision**: Approval/rejection actions complete synchronously in single request

**Rationale**:
- Simple operations that complete in <2 seconds
- No need for background job complexity
- Immediate feedback to admin
- Transactional consistency (status update + audit record in single transaction)

**Alternatives Considered**:
1. **Async job queue**: Adds complexity without benefit for fast operations
2. **Webhook-based**: Unnecessary indirection for internal operations
3. **Event-driven architecture**: Overkill for simple CRUD operations

**Trade-offs**:
- ✓ Simple implementation
- ✓ Immediate feedback
- ✓ Transactional consistency
- ✗ Request blocks until completion (acceptable given <2s target)

---

### Decision 8: Utility Scripts for Admin Management

**Decision**: Provide Python scripts (`make_admin.py`, `list_users.py`, `run_migration.py`) for admin operations

**Rationale**:
- Enables admin creation before admin panel is accessible
- Provides fallback for admin operations if UI fails
- Useful for automated deployment and testing
- Simple to run with `uv run python script.py`

**Alternatives Considered**:
1. **Database-only admin creation**: Requires SQL knowledge, error-prone
2. **API-only admin creation**: Chicken-and-egg problem (need admin to create admin)
3. **Environment variable for first admin**: Inflexible, requires redeployment to change

**Trade-offs**:
- ✓ Flexible admin management
- ✓ Useful for automation and testing
- ✓ Fallback if UI unavailable
- ✗ Requires backend access (acceptable for admin operations)

---

## Technology Choices

### Database Migration: Alembic

**Choice**: Use Alembic for database schema changes

**Rationale**:
- Already used in project for schema management
- Provides version control for database changes
- Supports rollback if needed
- Generates migration from model changes

**Alternatives**: Manual SQL scripts (less maintainable), SQLModel auto-create (no version control)

### Frontend State Management: React useState

**Choice**: Use local component state for admin panel

**Rationale**:
- Simple CRUD operations don't require global state
- Admin panel is isolated feature
- Reduces dependencies and complexity

**Alternatives**: Redux (overkill), Context API (unnecessary for isolated feature)

### API Client: Fetch API

**Choice**: Use native Fetch API for admin operations

**Rationale**:
- Consistent with existing API clients in project
- No additional dependencies
- Sufficient for simple REST operations

**Alternatives**: Axios (unnecessary dependency), GraphQL (overkill for CRUD)

---

## Performance Considerations

### Database Indexes

**Decision**: Add index on `account_status` column

**Rationale**:
- Admin panel frequently queries for pending users
- Login checks account status on every authentication
- Index improves query performance for status-based filtering

**Impact**: Minimal storage overhead, significant query performance improvement

### Query Optimization

**Decision**: Use single query to fetch user with status check during login

**Rationale**:
- Avoids N+1 query problem
- Reduces database round trips
- Acceptable latency (<100ms added to authentication)

---

## Security Considerations

### Admin Authorization

**Decision**: Verify admin status on every admin endpoint request

**Rationale**:
- Defense in depth (frontend + backend checks)
- Prevents privilege escalation
- Consistent with existing authorization pattern

**Implementation**: Dependency injection in FastAPI routes checks `approval_flags.is_admin`

### Audit Trail

**Decision**: Record admin_id and timestamp for all approval actions

**Rationale**:
- Compliance requirement for access control decisions
- Debugging and accountability
- Immutable audit log (no updates/deletes)

**Storage**: Stored in user record (approved_by, approved_at, rejection_reason)

---

## Future Enhancements

### Identified During Implementation

1. **Email Service Integration**: Replace console logging with SMTP/SendGrid/AWS SES
2. **Bulk Operations**: Approve/reject multiple users at once
3. **Approval Workflow**: Multi-stage approval for high-risk registrations
4. **Analytics Dashboard**: Track approval rates, response times, rejection reasons
5. **Appeal Process**: Allow rejected users to appeal decision
6. **Automated Approval**: Auto-approve users from trusted email domains

### Not Implemented (Out of Scope)

- Role-based access control (RBAC) beyond admin/user
- Temporary or time-limited approvals
- Integration with external identity verification services
- User self-service account management

---

## Lessons Learned

### What Worked Well

1. **Extending existing model**: Simpler than separate tables, better performance
2. **Auto-approving existing users**: Zero disruption to current users
3. **Utility scripts**: Invaluable for initial setup and testing
4. **Console logging for emails**: Allowed feature deployment without email service

### What Could Be Improved

1. **Earlier specification**: Retroactive spec/plan created after implementation
2. **Test coverage**: Manual testing only, no automated tests written
3. **Email templates**: Hardcoded messages, should be configurable
4. **Error handling**: Basic error messages, could be more user-friendly

---

## References

- Feature Specification: [spec.md](./spec.md)
- Implementation Plan: [plan.md](./plan.md)
- Data Model: [data-model.md](./data-model.md)
- API Contracts: [contracts/](./contracts/)
- Setup Guide: [quickstart.md](./quickstart.md)
