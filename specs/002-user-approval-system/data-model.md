# Data Model: User Approval System

**Feature**: 002-user-approval-system  
**Date**: 2026-04-13  
**Status**: Implemented

---

## Overview

This document describes the database schema and entity relationships for the user approval system. The implementation extends the existing User model with approval-related fields rather than creating separate entities.

---

## Entity: User (Extended)

### Table: `users`

**Description**: Core user entity extended with approval workflow fields

**Primary Key**: `id` (UUID)

### Fields

| Field Name | Type | Nullable | Default | Description |
|------------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key, unique user identifier |
| `email` | VARCHAR | No | - | User email address (unique) |
| `name` | VARCHAR | Yes | NULL | User display name |
| `hashed_password` | VARCHAR | No | - | Bcrypt hashed password |
| `is_active` | BOOLEAN | No | true | Account active flag |
| `approval_flags` | JSON | Yes | NULL | Flexible permissions object |
| `account_status` | VARCHAR | No | 'pending' | Approval status: pending, approved, rejected |
| `approved_by` | UUID | Yes | NULL | Foreign key to admin user who approved/rejected |
| `approved_at` | TIMESTAMP | Yes | NULL | Timestamp of approval/rejection action |
| `rejection_reason` | VARCHAR | Yes | NULL | Admin-provided reason for rejection |
| `created_at` | TIMESTAMP | No | now() | Account creation timestamp |
| `updated_at` | TIMESTAMP | No | now() | Last update timestamp |
| `reset_token` | VARCHAR | Yes | NULL | Password reset token |
| `reset_token_expires` | TIMESTAMP | Yes | NULL | Password reset token expiration |
| `fbr_access_token` | VARCHAR | Yes | NULL | FBR API access token (deprecated) |
| `fbr_sandbox_token` | VARCHAR | Yes | NULL | FBR sandbox environment token |
| `fbr_production_token` | VARCHAR | Yes | NULL | FBR production environment token |
| `fbr_environment` | VARCHAR | Yes | 'SANDBOX' | Current FBR environment preference |
| `fbr_seller_ntn` | VARCHAR | Yes | NULL | FBR seller NTN number |
| `fbr_business_name` | VARCHAR | Yes | NULL | Business name for FBR |
| `fbr_seller_province` | VARCHAR | Yes | NULL | Seller province |
| `fbr_seller_address` | VARCHAR | Yes | NULL | Seller address |

### Indexes

| Index Name | Columns | Type | Purpose |
|------------|---------|------|---------|
| `ix_users_email` | `email` | UNIQUE | Fast email lookup for authentication |
| `ix_users_account_status` | `account_status` | BTREE | Fast filtering by approval status |

### Constraints

- **Primary Key**: `id`
- **Unique**: `email`
- **Foreign Key**: `approved_by` references `users(id)` (self-referential)
- **Check**: `account_status` IN ('pending', 'approved', 'rejected')

---

## Field Details

### account_status

**Type**: VARCHAR (enum-like)  
**Values**: 
- `'pending'` - User registered but not yet approved
- `'approved'` - User approved by admin, can login
- `'rejected'` - User rejected by admin, cannot login

**State Transitions**:
```
pending → approved (via admin approval)
pending → rejected (via admin rejection)
```

**Business Rules**:
- New users default to 'pending'
- Existing users migrated to 'approved'
- Status changes are permanent (no reversal workflow)
- Only admins can change status

### approval_flags

**Type**: JSON  
**Structure**:
```json
{
  "is_admin": boolean,
  "has_production_access": boolean,
  "can_post_to_production": boolean
}
```

**Purpose**: Flexible permission system for user capabilities

**Admin Detection**: User is admin if `approval_flags.is_admin === true`

### approved_by

**Type**: UUID (Foreign Key)  
**References**: `users.id`  
**Purpose**: Audit trail - records which admin performed approval/rejection

**Business Rules**:
- Set when status changes from 'pending' to 'approved' or 'rejected'
- Immutable once set
- Self-referential foreign key (admin is also a user)

### approved_at

**Type**: TIMESTAMP  
**Purpose**: Audit trail - records when approval/rejection occurred

**Business Rules**:
- Set when status changes from 'pending'
- Immutable once set
- Used for compliance reporting

### rejection_reason

**Type**: VARCHAR  
**Purpose**: Admin-provided explanation for rejection

**Business Rules**:
- Required when rejecting user
- NULL for approved users
- Displayed to user on login attempt
- Stored for audit purposes

---

## Relationships

### Self-Referential: User → User (Admin)

**Type**: Many-to-One (optional)  
**Foreign Key**: `approved_by` → `users.id`  
**Description**: Links user to the admin who approved/rejected them

**Cardinality**:
- One admin can approve/reject many users
- One user can be approved/rejected by one admin
- Relationship is optional (NULL for pending users)

**Query Example**:
```sql
SELECT 
  u.email,
  u.account_status,
  admin.email as approved_by_email,
  u.approved_at
FROM users u
LEFT JOIN users admin ON u.approved_by = admin.id
WHERE u.account_status != 'pending';
```

---

## State Machine

### User Account Status

```
┌─────────┐
│ pending │ (initial state for new registrations)
└────┬────┘
     │
     ├─────────────┐
     │             │
     ▼             ▼
┌──────────┐  ┌──────────┐
│ approved │  │ rejected │ (terminal states)
└──────────┘  └──────────┘
```

**Transitions**:
1. **Registration** → `pending`
   - Trigger: User submits registration form
   - Actor: System
   - Side effects: Admin notification sent

2. **Approval** → `approved`
   - Trigger: Admin clicks "Approve"
   - Actor: Admin user
   - Side effects: 
     - `approved_by` set to admin ID
     - `approved_at` set to current timestamp
     - User notification sent
     - User can now login

3. **Rejection** → `rejected`
   - Trigger: Admin clicks "Reject" and provides reason
   - Actor: Admin user
   - Side effects:
     - `approved_by` set to admin ID
     - `approved_at` set to current timestamp
     - `rejection_reason` set to admin input
     - User notification sent
     - User cannot login

**Invariants**:
- Status can only transition from 'pending' to 'approved' or 'rejected'
- Once approved or rejected, status cannot change
- `approved_by` and `approved_at` must be set together
- `rejection_reason` must be set when status is 'rejected'

---

## Migration Strategy

### Migration: a1b2c3d4e5f7_add_user_approval_fields

**Operations**:
1. Add `account_status` column (VARCHAR, NOT NULL, DEFAULT 'pending')
2. Add `approved_by` column (UUID, NULLABLE)
3. Add `approved_at` column (TIMESTAMP, NULLABLE)
4. Add `rejection_reason` column (VARCHAR, NULLABLE)
5. Create index on `account_status`
6. Update existing users: SET `account_status = 'approved'`

**Rollback**:
1. Drop index on `account_status`
2. Drop `rejection_reason` column
3. Drop `approved_at` column
4. Drop `approved_by` column
5. Drop `account_status` column

**Data Migration**:
- All existing users set to 'approved' status
- No data loss
- Backward compatible (existing users unaffected)

---

## Query Patterns

### Get Pending Users (Admin Panel)

```sql
SELECT id, email, name, created_at, account_status
FROM users
WHERE account_status = 'pending'
ORDER BY created_at DESC;
```

**Index Used**: `ix_users_account_status`  
**Performance**: O(log n) with index

### Check User Status (Login)

```sql
SELECT id, email, hashed_password, account_status, rejection_reason
FROM users
WHERE email = ?;
```

**Index Used**: `ix_users_email` (unique)  
**Performance**: O(1) hash lookup

### Get Approval Audit Trail

```sql
SELECT 
  u.email as user_email,
  u.account_status,
  u.approved_at,
  admin.email as approved_by_email,
  u.rejection_reason
FROM users u
LEFT JOIN users admin ON u.approved_by = admin.id
WHERE u.account_status IN ('approved', 'rejected')
ORDER BY u.approved_at DESC;
```

**Index Used**: `ix_users_account_status`  
**Performance**: O(log n) with index, O(n) for join

---

## Validation Rules

### account_status
- Must be one of: 'pending', 'approved', 'rejected'
- Cannot be NULL
- Cannot be empty string

### email
- Must be valid email format
- Must be unique across all users
- Cannot be NULL or empty

### approved_by
- Must reference existing user ID if not NULL
- Referenced user must have `approval_flags.is_admin = true`

### rejection_reason
- Required (not NULL) when `account_status = 'rejected'`
- Must be NULL when `account_status != 'rejected'`
- Maximum length: 500 characters

### approved_at
- Must be set when status changes from 'pending'
- Must be NULL when status is 'pending'
- Cannot be in the future

---

## Storage Estimates

### Per User Record

**Base User Data**: ~200 bytes  
**Approval Fields**: ~100 bytes  
- `account_status`: 10 bytes
- `approved_by`: 16 bytes (UUID)
- `approved_at`: 8 bytes (timestamp)
- `rejection_reason`: ~50 bytes average

**Total per user**: ~300 bytes

### Scale Projections

| Users | Storage | Index Overhead | Total |
|-------|---------|----------------|-------|
| 100 | 30 KB | 10 KB | 40 KB |
| 1,000 | 300 KB | 100 KB | 400 KB |
| 10,000 | 3 MB | 1 MB | 4 MB |
| 100,000 | 30 MB | 10 MB | 40 MB |

**Conclusion**: Storage overhead is negligible even at large scale

---

## Security Considerations

### Data Protection

- **Password**: Hashed with bcrypt (never stored in plaintext)
- **Tokens**: FBR tokens encrypted at rest (application-level)
- **Email**: Considered PII, protected by row-level security

### Access Control

- **Users**: Can only read their own record
- **Admins**: Can read all users, update approval status only
- **System**: Can create users (registration), update status (approval workflow)

### Audit Requirements

- All approval/rejection actions logged with admin ID and timestamp
- Rejection reasons stored for compliance
- Audit trail immutable (no updates/deletes)

---

## References

- Feature Specification: [spec.md](./spec.md)
- Implementation Plan: [plan.md](./plan.md)
- Research & Decisions: [research.md](./research.md)
- API Contracts: [contracts/](./contracts/)
