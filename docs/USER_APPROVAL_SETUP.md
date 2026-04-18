# User Approval System - Setup Guide

## Overview

The system now requires admin approval for new user registrations. When users register, their accounts are set to "pending" status and they cannot log in until an administrator approves them.

## Setup Steps

### 1. Apply Database Migration

Since alembic command is not available, run the SQL migration manually:

**Option A: Using psql command line**
```bash
psql -h <your-neon-host> -U <username> -d <database> -f manual_migration.sql
```

**Option B: Using Neon Console**
1. Go to your Neon dashboard
2. Open SQL Editor
3. Copy and paste the contents of `manual_migration.sql`
4. Execute the query

**Option C: Using Python script**
```bash
cd backend
python -c "
from sqlalchemy import text
from src.database.session import engine

with engine.connect() as conn:
    with open('manual_migration.sql', 'r') as f:
        sql = f.read()
        for statement in sql.split(';'):
            if statement.strip():
                conn.execute(text(statement))
        conn.commit()
print('Migration applied successfully!')
"
```

### 2. Create First Admin User

**Option A: Register normally, then promote to admin**
1. Register a new user account at http://localhost:3000/register
2. Run the make_admin script:
```bash
cd backend
python make_admin.py your-email@example.com
```

**Option B: Directly in database**
```sql
-- Find your user ID
SELECT id, email, account_status FROM users WHERE email = 'your-email@example.com';

-- Make user admin
UPDATE users 
SET 
  account_status = 'approved',
  approval_flags = '{"is_admin": true}'::jsonb
WHERE email = 'your-email@example.com';
```

### 3. Access Admin Panel

Once you're an admin, access the admin panel at:
```
http://localhost:3000/admin/users
```

## How It Works

### User Registration Flow

1. **User registers** → Account created with `account_status = 'pending'`
2. **Admin notification** → Email sent to admin (currently logs to console)
3. **User sees success message** → "Your account is pending admin approval"
4. **User cannot login** → Login blocked until approved

### Admin Approval Flow

1. **Admin logs in** → Access admin panel at `/admin/users`
2. **View pending users** → See all users awaiting approval
3. **Approve or Reject** → 
   - Approve: User can now log in
   - Reject: User cannot log in, sees rejection reason
4. **Email notification** → User receives approval/rejection email (currently logs to console)

### Login Behavior

- **Pending users**: Cannot log in, see "Your account is pending admin approval"
- **Rejected users**: Cannot log in, see rejection reason
- **Approved users**: Can log in normally

## API Endpoints

### Admin Endpoints (Require admin authentication)

- `GET /api/v1/admin/users/pending` - Get all pending users
- `GET /api/v1/admin/users/all?status_filter=<status>` - Get all users with optional filter
- `POST /api/v1/admin/users/{user_id}/approve` - Approve a user
- `POST /api/v1/admin/users/{user_id}/reject` - Reject a user (with reason)
- `DELETE /api/v1/admin/users/{user_id}` - Delete a user

### Auth Endpoints

- `POST /api/v1/auth/register` - Register new user (returns pending status)
- `POST /api/v1/auth/login` - Login (checks account status)

## Email Notifications

Currently, email notifications are logged to the console. To enable actual email sending:

1. Edit `backend/src/utils/email_utils.py`
2. Uncomment and configure SMTP settings in the TODO sections
3. Add SMTP configuration to `backend/src/config/settings.py`:
```python
smtp_host: str = "smtp.gmail.com"
smtp_port: int = 587
smtp_from_email: str = "noreply@yourcompany.com"
smtp_password: str = ""
admin_email: str = "admin@yourcompany.com"
```

## Testing the Flow

### Test New User Registration

1. Go to http://localhost:3000/register
2. Fill in registration form
3. Submit
4. Should see: "Registration successful! Your account is pending admin approval"
5. Try to login → Should be blocked with pending message

### Test Admin Approval

1. Login as admin
2. Go to http://localhost:3000/admin/users
3. See the pending user in the list
4. Click "Approve"
5. User should now be able to log in

### Test Admin Rejection

1. Login as admin
2. Go to http://localhost:3000/admin/users
3. Click "Reject" on a pending user
4. Enter rejection reason
5. User should see rejection message when trying to log in

## Security Notes

- Admin access is controlled by `approval_flags.is_admin = true`
- Only approved admins can access admin endpoints
- Admins cannot delete themselves
- All existing users are automatically approved during migration

## Troubleshooting

### "User not found" when running make_admin.py
- Ensure the email address is correct
- Check database connection in `.env` file

### Cannot access admin panel
- Ensure your user has `approval_flags.is_admin = true`
- Check browser console for errors
- Verify you're logged in

### Migration fails
- Check database connection
- Ensure you have proper permissions
- Try running SQL statements one by one

## Future Enhancements

- Role-based access control (RBAC)
- Email templates with HTML
- Bulk approve/reject
- User activity logs
- Admin dashboard with statistics
