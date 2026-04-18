# Quickstart Guide: User Approval System

**Feature**: 002-user-approval-system  
**Date**: 2026-04-13  
**Status**: Implemented

---

## Overview

This guide provides step-by-step instructions for setting up and using the user approval system. The system requires admin approval for all new user registrations to ensure only legitimate users can access the FBR invoice integration portal.

---

## Prerequisites

- Backend running (FastAPI on port 8001)
- Frontend running (Next.js on port 3000)
- Neon PostgreSQL database configured
- Python 3.13+ with uv package manager
- Node.js 18+ with npm/yarn

---

## Setup Instructions

### Step 1: Apply Database Migration

The user approval system requires new database columns. Apply the migration using one of these methods:

**Option A: Using Python script (Recommended)**

```bash
cd backend
uv run python run_migration.py
```

**Option B: Using Alembic (if available)**

```bash
cd backend
alembic upgrade head
```

**Option C: Manual SQL (if scripts unavailable)**

```bash
# Connect to your Neon database and run:
psql -h <neon-host> -U <username> -d <database> -f manual_migration.sql
```

**Expected Output**:
```
Connecting to database...
Applying migration...
  - Adding account_status column...
  - Adding approved_by column...
  - Adding approved_at column...
  - Adding rejection_reason column...
  - Creating index on account_status...
  - Updating existing users to 'approved' status...
    Updated 4 existing users

[SUCCESS] Migration completed successfully!
```

### Step 2: Create First Admin User

You need at least one admin user to approve registrations. Choose one method:

**Option A: Promote existing user to admin**

```bash
cd backend

# List all users to find the email
uv run python list_users.py

# Make user an admin
uv run python make_admin.py user@example.com
```

**Expected Output**:
```
[SUCCESS] User 'user@example.com' is now an admin!
  User ID: 3ad96c98-3c48-48cf-bb46-03af4bbe2249
  Name: John Doe
  Status: approved
```

**Option B: Direct database update**

```sql
-- Find your user
SELECT id, email, account_status FROM users WHERE email = 'your-email@example.com';

-- Make user admin
UPDATE users 
SET 
  account_status = 'approved',
  approval_flags = '{"is_admin": true}'::jsonb
WHERE email = 'your-email@example.com';
```

### Step 3: Verify Setup

1. **Check backend is running**:
   ```bash
   curl http://localhost:8001/health
   # Expected: {"status":"healthy","service":"fbr-invoice-portal-backend"}
   ```

2. **Check admin endpoints are accessible**:
   ```bash
   # Login as admin first to get token
   curl -X POST http://localhost:8001/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"your-password"}'
   
   # Use token to access admin endpoint
   curl http://localhost:8001/api/v1/admin/users/pending \
     -H "Authorization: Bearer <your-token>"
   ```

3. **Check frontend is running**:
   - Open http://localhost:3000
   - Login as admin
   - Navigate to http://localhost:3000/admin/users
   - Should see admin panel

---

## Usage Guide

### For New Users

#### 1. Register for Account

1. Go to http://localhost:3000/register
2. Fill in registration form:
   - Email address
   - Password (minimum 8 characters)
   - Full name
3. Click "Create Account"
4. See success message: "Registration successful! Your account is pending admin approval"
5. Wait for admin approval email

#### 2. Check Registration Status

**Cannot login until approved**. If you try to login:
- **Pending**: "Your account is pending admin approval. Please wait for approval before logging in."
- **Rejected**: "Your account has been rejected. Reason: [admin's reason]"
- **Approved**: Login succeeds, redirected to dashboard

#### 3. After Approval

1. Receive approval email notification
2. Go to http://localhost:3000/login
3. Enter your credentials
4. Successfully login and access the system

### For Administrators

#### 1. Access Admin Panel

1. Login at http://localhost:3000/login
2. Navigate to http://localhost:3000/admin/users
3. See two tabs:
   - **Pending Approvals**: Users waiting for approval
   - **All Users**: Complete user list with filters

#### 2. Review Pending Registrations

**Admin Panel shows**:
- User name
- Email address
- Registration date
- Current status

**Actions available**:
- Approve user
- Reject user (with reason)
- Delete user

#### 3. Approve User

1. Find user in "Pending Approvals" tab
2. Click "Approve" button
3. Confirmation: "User approved successfully!"
4. User receives approval email
5. User can now login

**What happens**:
- User status changes to "approved"
- Your admin ID recorded as approver
- Approval timestamp recorded
- Email notification sent to user

#### 4. Reject User

1. Find user in "Pending Approvals" tab
2. Click "Reject" button
3. Modal appears: "Reject User Registration"
4. Enter rejection reason (required)
5. Click "Confirm Reject"
6. Confirmation: "User rejected successfully!"
7. User receives rejection email with reason

**What happens**:
- User status changes to "rejected"
- Your admin ID recorded as rejector
- Rejection timestamp and reason recorded
- Email notification sent to user with reason
- User cannot login (sees rejection message)

#### 5. Delete User

1. Go to "All Users" tab
2. Find user to delete
3. Click "Delete" button
4. Confirm deletion
5. User permanently removed from system

**Restrictions**:
- Cannot delete your own account
- Confirmation required to prevent accidents
- Action is permanent (no undo)

#### 6. View All Users

**All Users tab shows**:
- All users regardless of status
- Filter by status: pending, approved, rejected
- User details: name, email, status, approval date
- Actions: Delete (for any status)

**Use cases**:
- Audit user list
- Find specific user
- Review approval history
- Clean up rejected/test accounts

---

## Email Notifications

### Current Implementation

Email notifications are currently **logged to console** (not sent via email). This allows the system to function without email service configuration.

**Console output example**:
```
================================================================================
NEW USER REGISTRATION - ADMIN NOTIFICATION
================================================================================
To: admin@company.com
Subject: New User Registration Pending Approval

User Details:
  Name: John Doe
  Email: john@example.com
  User ID: 3ad96c98-3c48-48cf-bb46-03af4bbe2249

Action Required:
  Please log in to the admin panel to approve or reject this user.
  Admin Panel: http://localhost:3000/admin/users
================================================================================
```

### Enable Real Email (Optional)

To send actual emails instead of console logs:

1. **Configure SMTP settings** in `backend/src/config/settings.py`:
   ```python
   smtp_host: str = "smtp.gmail.com"
   smtp_port: int = 587
   smtp_from_email: str = "noreply@yourcompany.com"
   smtp_password: str = ""
   admin_email: str = "admin@yourcompany.com"
   ```

2. **Add to `.env` file**:
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_FROM_EMAIL=noreply@yourcompany.com
   SMTP_PASSWORD=your-app-password
   ADMIN_EMAIL=admin@yourcompany.com
   ```

3. **Update email functions** in `backend/src/utils/email_utils.py`:
   - Uncomment SMTP code in TODO sections
   - Test email sending

---

## Troubleshooting

### Migration Issues

**Problem**: Migration fails with "column already exists"

**Solution**: Migration already applied, skip this step

---

**Problem**: Migration fails with "permission denied"

**Solution**: Check database connection string in `.env` file

---

**Problem**: "No module named 'sqlalchemy'"

**Solution**: Run migration with uv:
```bash
uv run python run_migration.py
```

---

### Admin Access Issues

**Problem**: "Admin access required" when accessing admin panel

**Solution**: Verify user has admin flag:
```bash
uv run python list_users.py
# Check if "Is Admin" column shows "Yes"

# If not, make user admin:
uv run python make_admin.py your-email@example.com
```

---

**Problem**: Cannot find make_admin.py script

**Solution**: Script is in backend directory:
```bash
cd backend
ls -la make_admin.py
```

---

### Login Issues

**Problem**: "Your account is pending admin approval"

**Solution**: Wait for admin to approve your account, or contact admin

---

**Problem**: "Your account has been rejected"

**Solution**: Contact admin to understand rejection reason and reapply if appropriate

---

**Problem**: Existing user cannot login after migration

**Solution**: Check user status in database:
```sql
SELECT email, account_status FROM users WHERE email = 'user@example.com';
```

If status is 'pending', update to 'approved':
```sql
UPDATE users SET account_status = 'approved' WHERE email = 'user@example.com';
```

---

### Frontend Issues

**Problem**: Admin panel shows blank page

**Solution**: 
1. Check browser console for errors
2. Verify backend is running: `curl http://localhost:8001/health`
3. Verify you're logged in as admin
4. Clear browser cache and reload

---

**Problem**: "Failed to fetch pending users"

**Solution**:
1. Check backend logs for errors
2. Verify admin endpoints are accessible
3. Check JWT token is valid (try logging out and back in)

---

## API Examples

### Register New User

```bash
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePass123!",
    "name": "New User"
  }'
```

**Response**:
```json
{
  "message": "Registration successful! Your account is pending admin approval.",
  "email": "newuser@example.com",
  "status": "pending_approval"
}
```

### Login (Approved User)

```bash
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "approved@example.com",
    "password": "SecurePass123!"
  }'
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "3ad96c98-3c48-48cf-bb46-03af4bbe2249",
    "email": "approved@example.com",
    "name": "Approved User",
    "is_active": true
  }
}
```

### Get Pending Users (Admin)

```bash
curl http://localhost:8001/api/v1/admin/users/pending \
  -H "Authorization: Bearer <admin-token>"
```

**Response**:
```json
{
  "total": 2,
  "users": [
    {
      "id": "uuid-1",
      "email": "pending1@example.com",
      "name": "Pending User 1",
      "created_at": "2026-04-13T10:30:00Z",
      "account_status": "pending"
    },
    {
      "id": "uuid-2",
      "email": "pending2@example.com",
      "name": "Pending User 2",
      "created_at": "2026-04-13T11:45:00Z",
      "account_status": "pending"
    }
  ]
}
```

### Approve User (Admin)

```bash
curl -X POST http://localhost:8001/api/v1/admin/users/uuid-1/approve \
  -H "Authorization: Bearer <admin-token>"
```

**Response**:
```json
{
  "success": true,
  "message": "User pending1@example.com has been approved",
  "user": {
    "id": "uuid-1",
    "email": "pending1@example.com",
    "name": "Pending User 1",
    "account_status": "approved",
    "approved_at": "2026-04-13T12:00:00Z"
  }
}
```

### Reject User (Admin)

```bash
curl -X POST http://localhost:8001/api/v1/admin/users/uuid-2/reject \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Invalid business credentials"
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "User pending2@example.com has been rejected",
  "user": {
    "id": "uuid-2",
    "email": "pending2@example.com",
    "name": "Pending User 2",
    "account_status": "rejected",
    "rejection_reason": "Invalid business credentials"
  }
}
```

---

## Security Notes

- Admin panel requires authentication (JWT token)
- Admin endpoints verify `approval_flags.is_admin = true`
- Users can only access their own data (row-level security)
- Passwords are hashed with bcrypt (never stored in plaintext)
- Approval actions are logged with admin ID and timestamp
- Audit trail is immutable (no updates/deletes)

---

## Next Steps

After setup is complete:

1. **Test the workflow**:
   - Register a test user
   - Approve/reject from admin panel
   - Verify email notifications (console logs)
   - Test login with different statuses

2. **Configure email** (optional):
   - Set up SMTP service
   - Update email_utils.py
   - Test email delivery

3. **Monitor usage**:
   - Check pending users regularly
   - Review approval/rejection patterns
   - Adjust workflow as needed

4. **Future enhancements**:
   - Bulk approval operations
   - Automated approval rules
   - Analytics dashboard
   - Appeal process for rejected users

---

## Support

For issues or questions:
- Check troubleshooting section above
- Review implementation documentation: `IMPLEMENTATION_SUMMARY.md`
- Check backend logs for errors
- Verify database migration status

---

## References

- Feature Specification: [spec.md](./spec.md)
- Implementation Plan: [plan.md](./plan.md)
- Data Model: [data-model.md](./data-model.md)
- API Contracts: [contracts/](./contracts/)
- Research & Decisions: [research.md](./research.md)
