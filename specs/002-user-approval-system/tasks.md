# Implementation Tasks: User Approval System

**Feature**: 002-user-approval-system  
**Branch**: `002-user-approval-system`  
**Status**: Implemented (Retroactive Documentation)  
**Created**: 2026-04-13

---

## Overview

This document organizes implementation tasks for the user approval system feature. Tasks are grouped by user story to enable independent implementation and testing. Since this feature is already implemented, this serves as retroactive documentation of the implementation sequence.

---

## User Stories (from spec.md)

- **US1**: User Registration with Pending Status - New users register but cannot login until approved
- **US2**: Admin Panel for User Management - Admins can view, approve, reject, and delete users
- **US3**: Notification System - Users and admins receive email notifications for registration and approval events
- **US4**: Access Control - Admin panel restricted to authorized administrators only

---

## Implementation Strategy

**MVP Scope**: US1 + US2 (Core approval workflow)  
**Delivery Approach**: Incremental by user story  
**Parallel Opportunities**: Frontend and backend tasks within each story can run in parallel

---

## Phase 1: Setup & Infrastructure

**Goal**: Prepare database schema and project structure for approval workflow

### Database Migration

- [ ] T001 Create Alembic migration file for user approval fields in backend/alembic/versions/
- [ ] T002 Add account_status column (VARCHAR, NOT NULL, DEFAULT 'pending') to users table
- [ ] T003 Add approved_by column (UUID, NULLABLE) to users table
- [ ] T004 Add approved_at column (TIMESTAMP, NULLABLE) to users table
- [ ] T005 Add rejection_reason column (VARCHAR, NULLABLE) to users table
- [ ] T006 Create index on account_status column for query performance
- [ ] T007 Add data migration to set existing users to 'approved' status
- [ ] T008 Create migration utility script backend/run_migration.py

### Utility Scripts

- [ ] T009 [P] Create admin management script backend/make_admin.py
- [ ] T010 [P] Create user listing script backend/list_users.py
- [ ] T011 [P] Create setup documentation backend/USER_APPROVAL_SETUP.md

---

## Phase 2: Foundational - Data Model & Auth Updates

**Goal**: Extend user model and update authentication logic (blocking prerequisite for all user stories)

### Backend - User Model Extension

- [ ] T012 Update User model in backend/src/models/user.py with approval fields
- [ ] T013 Add account_status field with default 'pending' to UserBase schema
- [ ] T014 Add approved_by, approved_at, rejection_reason fields to User model
- [ ] T015 Update UserRead schema to include account_status field

### Backend - Authentication Updates

- [ ] T016 Update login endpoint in backend/src/api/v1/auth.py to check account_status
- [ ] T017 Add status check: block login if account_status is 'pending'
- [ ] T018 Add status check: block login if account_status is 'rejected' with reason
- [ ] T019 Update registration endpoint to set account_status='pending' for new users
- [ ] T020 Update registration response to return pending_approval status instead of token

---

## Phase 3: US1 - User Registration with Pending Status

**User Story**: As a new user, I want to register for an account that requires admin approval, so that only legitimate users can access the system.

**Independent Test Criteria**:
- ✓ New user can register with email, password, and name
- ✓ Registration returns success message with pending status (no access token)
- ✓ Pending user cannot login (receives "pending approval" message)
- ✓ Rejected user cannot login (receives rejection reason)
- ✓ Approved user can login successfully

### Frontend - Registration Flow

- [ ] T021 [P] [US1] Update registration page in frontend/src/app/(auth)/register/page.tsx
- [ ] T022 [P] [US1] Add success state for pending approval in registration page
- [ ] T023 [P] [US1] Display pending approval message after successful registration
- [ ] T024 [P] [US1] Add "Back to Login" button for pending approval state
- [ ] T025 [US1] Update auth provider in frontend/src/providers/auth-provider.tsx
- [ ] T026 [US1] Handle pending_approval status in signUp function
- [ ] T027 [US1] Prevent auto-login for pending users

### Documentation

- [ ] T028 [P] [US1] Document registration flow in specs/002-user-approval-system/quickstart.md

---

## Phase 4: US2 - Admin Panel for User Management

**User Story**: As an administrator, I want to view pending registrations and approve/reject users, so that I can control who accesses the system.

**Independent Test Criteria**:
- ✓ Admin can access admin panel at /admin/users
- ✓ Admin can view list of pending users with details
- ✓ Admin can view list of all users with status filter
- ✓ Admin can approve pending user (status changes to approved, user can login)
- ✓ Admin can reject pending user with reason (status changes to rejected, reason stored)
- ✓ Admin can delete users (except themselves)
- ✓ Non-admin users cannot access admin panel (403 Forbidden)

### Backend - Admin API Endpoints

- [ ] T029 [US2] Create admin router in backend/src/api/v1/admin.py
- [ ] T030 [US2] Implement require_admin dependency for authorization
- [ ] T031 [US2] Create GET /admin/users/pending endpoint
- [ ] T032 [P] [US2] Create GET /admin/users/all endpoint with status filter
- [ ] T033 [P] [US2] Create POST /admin/users/{user_id}/approve endpoint
- [ ] T034 [P] [US2] Create POST /admin/users/{user_id}/reject endpoint with reason
- [ ] T035 [P] [US2] Create DELETE /admin/users/{user_id} endpoint
- [ ] T036 [US2] Add admin router to main.py with /api/v1/admin prefix

### Backend - Admin Authorization

- [ ] T037 [US2] Implement admin check in require_admin dependency
- [ ] T038 [US2] Verify approval_flags.is_admin = true for admin access
- [ ] T039 [US2] Return 403 Forbidden for non-admin users

### Backend - Approval Logic

- [ ] T040 [US2] Implement user approval logic (update status, set approved_by, set approved_at)
- [ ] T041 [US2] Implement user rejection logic (update status, set approved_by, set approved_at, set rejection_reason)
- [ ] T042 [US2] Implement user deletion logic (prevent self-deletion)
- [ ] T043 [US2] Add transaction handling for approval/rejection actions

### Frontend - Admin Panel UI

- [ ] T044 [P] [US2] Create admin users page in frontend/src/app/(protected)/admin/users/page.tsx
- [ ] T045 [P] [US2] Implement pending users tab with user list
- [ ] T046 [P] [US2] Implement all users tab with status filter
- [ ] T047 [P] [US2] Add approve button with confirmation
- [ ] T048 [P] [US2] Add reject button with reason modal
- [ ] T049 [P] [US2] Add delete button with confirmation
- [ ] T050 [P] [US2] Add refresh button to reload user list
- [ ] T051 [P] [US2] Implement status badges (pending, approved, rejected)
- [ ] T052 [P] [US2] Add loading states for actions

### Frontend - Admin API Client

- [ ] T053 [P] [US2] Create admin API client in frontend/src/services/adminApi.ts
- [ ] T054 [P] [US2] Implement getPendingUsers method
- [ ] T055 [P] [US2] Implement getAllUsers method with status filter
- [ ] T056 [P] [US2] Implement approveUser method
- [ ] T057 [P] [US2] Implement rejectUser method
- [ ] T058 [P] [US2] Implement deleteUser method

### Documentation

- [ ] T059 [P] [US2] Document admin panel usage in specs/002-user-approval-system/quickstart.md
- [ ] T060 [P] [US2] Create API contract specs/002-user-approval-system/contracts/admin-api.yaml

---

## Phase 5: US3 - Notification System

**User Story**: As a user or admin, I want to receive email notifications for registration and approval events, so that I'm informed of account status changes.

**Independent Test Criteria**:
- ✓ Admin receives notification when new user registers
- ✓ User receives notification when account is approved
- ✓ User receives notification when account is rejected (with reason)
- ✓ Notifications are logged to console (SMTP integration optional)

### Backend - Email Utilities

- [ ] T061 [US3] Create email utilities module in backend/src/utils/email_utils.py
- [ ] T062 [P] [US3] Implement send_admin_notification_email function
- [ ] T063 [P] [US3] Implement send_approval_email function
- [ ] T064 [P] [US3] Implement send_rejection_email function
- [ ] T065 [US3] Add console logging for email notifications (SMTP TODO comments)

### Backend - Notification Integration

- [ ] T066 [US3] Call send_admin_notification_email in registration endpoint
- [ ] T067 [P] [US3] Call send_approval_email in approve endpoint
- [ ] T068 [P] [US3] Call send_rejection_email in reject endpoint
- [ ] T069 [US3] Add error handling for notification failures (don't block approval actions)

### Documentation

- [ ] T070 [P] [US3] Document email configuration in specs/002-user-approval-system/quickstart.md
- [ ] T071 [P] [US3] Add SMTP integration instructions to USER_APPROVAL_SETUP.md

---

## Phase 6: US4 - Access Control & Audit Trail

**User Story**: As a system administrator, I want admin panel access restricted to authorized users and all approval actions audited, so that the system is secure and compliant.

**Independent Test Criteria**:
- ✓ Only users with is_admin flag can access admin endpoints
- ✓ Non-admin users receive 403 Forbidden
- ✓ All approval/rejection actions record admin_id and timestamp
- ✓ Rejection reasons are stored and retrievable
- ✓ Audit trail is immutable (no updates/deletes)

### Backend - Access Control

- [ ] T072 [US4] Verify admin authorization in all admin endpoints
- [ ] T073 [US4] Add integration test for non-admin access denial
- [ ] T074 [US4] Verify admin cannot delete their own account

### Backend - Audit Trail

- [ ] T075 [US4] Verify approved_by is set on approval/rejection
- [ ] T076 [US4] Verify approved_at timestamp is set
- [ ] T077 [US4] Verify rejection_reason is stored for rejections
- [ ] T078 [US4] Add database constraints to prevent audit data modification

### Documentation

- [ ] T079 [P] [US4] Document security considerations in specs/002-user-approval-system/quickstart.md
- [ ] T080 [P] [US4] Document audit trail in specs/002-user-approval-system/data-model.md

---

## Phase 7: Polish & Cross-Cutting Concerns

**Goal**: Complete documentation, testing, and deployment preparation

### Documentation

- [ ] T081 Create implementation summary in IMPLEMENTATION_SUMMARY.md
- [ ] T082 Update main README.md with user approval system overview
- [ ] T083 Create testing guide in TESTING_GUIDE.md
- [ ] T084 Document manual SQL migration in backend/manual_migration.sql

### Deployment

- [ ] T085 Verify migration runs successfully on clean database
- [ ] T086 Test admin creation script with real user
- [ ] T087 Verify existing users are auto-approved during migration
- [ ] T088 Test complete workflow end-to-end (register → approve → login)

---

## Task Summary

**Total Tasks**: 88  
**Setup Phase**: 11 tasks  
**Foundational Phase**: 9 tasks  
**US1 (Registration)**: 8 tasks  
**US2 (Admin Panel)**: 32 tasks  
**US3 (Notifications)**: 11 tasks  
**US4 (Access Control)**: 9 tasks  
**Polish Phase**: 8 tasks

**Parallelizable Tasks**: 42 tasks marked with [P]

---

## Dependencies

### Story Completion Order

```
Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3-6 (User Stories) → Phase 7 (Polish)
                                          ↓
                                    US1, US2, US3, US4 (can be done in parallel after foundational)
```

### Critical Path

1. **Setup** (T001-T011): Database migration and utilities
2. **Foundational** (T012-T020): User model and auth updates (BLOCKS all user stories)
3. **US1** (T021-T028): Registration flow (independent)
4. **US2** (T029-T060): Admin panel (independent, but most valuable)
5. **US3** (T061-T071): Notifications (independent)
6. **US4** (T072-T080): Access control (independent)
7. **Polish** (T081-T088): Documentation and testing

### User Story Dependencies

- **US1**: Depends on Foundational (auth updates)
- **US2**: Depends on Foundational (user model)
- **US3**: Depends on US2 (approval endpoints to trigger notifications)
- **US4**: Depends on US2 (admin endpoints to audit)

**Recommended Order**: Setup → Foundational → US2 → US1 → US3 → US4 → Polish

---

## Parallel Execution Examples

### Within US2 (Admin Panel)

**Backend Team**:
- T029-T036: Admin API endpoints (sequential)
- T037-T043: Authorization and logic (after T029-T036)

**Frontend Team** (parallel with backend):
- T044-T052: Admin panel UI
- T053-T058: Admin API client

**Documentation Team** (parallel with both):
- T059-T060: Documentation and contracts

### Within US3 (Notifications)

**All parallelizable after T061**:
- T062: Admin notification function
- T063: Approval notification function
- T064: Rejection notification function
- T070-T071: Documentation

---

## MVP Scope

**Minimum Viable Product**: US1 + US2

**Includes**:
- Database migration (T001-T008)
- User model extension (T012-T015)
- Auth updates (T016-T020)
- Registration flow (T021-T028)
- Admin panel (T029-T060)

**Excludes** (can be added later):
- Email notifications (US3)
- Advanced access control (US4)
- Polish and documentation (Phase 7)

**Delivery**: MVP provides core approval workflow - users can register, admins can approve/reject, users can login after approval.

---

## Testing Strategy

Since this is retroactive documentation for an implemented feature, testing was performed manually during implementation:

### Manual Testing Performed

1. **Registration Flow**:
   - Register new user → verify pending status
   - Attempt login → verify blocked with pending message
   - Verify no access token returned

2. **Admin Panel**:
   - Login as admin → access /admin/users
   - View pending users → verify list displays correctly
   - Approve user → verify status changes, user can login
   - Reject user → verify status changes, reason stored
   - Delete user → verify removal

3. **Notifications**:
   - Register user → verify admin notification in console
   - Approve user → verify approval notification in console
   - Reject user → verify rejection notification in console

4. **Access Control**:
   - Non-admin user → verify cannot access /admin/users
   - Admin → verify can access all admin endpoints
   - Verify audit trail (approved_by, approved_at, rejection_reason)

### Automated Testing (Future Enhancement)

- Unit tests for approval logic
- Integration tests for admin endpoints
- E2E tests for complete workflow
- Contract tests for API endpoints

---

## Implementation Notes

### Already Implemented

This feature is fully implemented. Tasks above document the implementation sequence retroactively.

### Key Files Modified

**Backend**:
- `backend/src/models/user.py` - Extended with approval fields
- `backend/src/api/v1/auth.py` - Updated login/register
- `backend/src/api/v1/admin.py` - New admin endpoints
- `backend/src/utils/email_utils.py` - Email notifications
- `backend/src/main.py` - Added admin router

**Frontend**:
- `frontend/src/app/(auth)/register/page.tsx` - Updated registration
- `frontend/src/app/(protected)/admin/users/page.tsx` - Admin panel
- `frontend/src/services/adminApi.ts` - Admin API client
- `frontend/src/providers/auth-provider.tsx` - Updated signup

**Database**:
- `backend/alembic/versions/a1b2c3d4e5f7_add_user_approval_fields.py` - Migration

**Utilities**:
- `backend/run_migration.py` - Migration script
- `backend/make_admin.py` - Admin creation
- `backend/list_users.py` - User listing

---

## References

- Feature Specification: [spec.md](./spec.md)
- Implementation Plan: [plan.md](./plan.md)
- Data Model: [data-model.md](./data-model.md)
- API Contracts: [contracts/](./contracts/)
- Research & Decisions: [research.md](./research.md)
- Quickstart Guide: [quickstart.md](./quickstart.md)
