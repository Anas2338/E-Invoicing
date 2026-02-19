# Forgot Password Feature - Implementation Guide

## Overview
A complete password reset feature has been implemented for the FBR Invoice Portal, allowing users to securely reset their passwords via email.

## Features Implemented

### Backend (FastAPI)

1. **Database Schema Updates**
   - Added `reset_token` field to store password reset tokens
   - Added `reset_token_expires` field to track token expiration (1 hour)
   - Location: `backend/src/models/user.py`

2. **Password Reset Service**
   - Token generation using secure random tokens
   - Token validation with expiration checking
   - Password hashing and reset functionality
   - Email notification system (console output for development)
   - Location: `backend/src/services/password_reset_service.py`

3. **API Endpoints**
   - `POST /api/v1/password-reset/request` - Request password reset
   - `POST /api/v1/password-reset/verify` - Verify reset token
   - `POST /api/v1/password-reset/confirm` - Confirm password reset
   - Location: `backend/src/api/v1/password_reset.py`

### Frontend (Next.js)

1. **Forgot Password Page**
   - URL: `/auth/forgot-password`
   - Email input form
   - Success confirmation screen
   - Location: `frontend/src/app/auth/forgot-password/page.tsx`

2. **Reset Password Page**
   - URL: `/auth/reset-password?token=<reset_token>`
   - Token verification on page load
   - New password input with confirmation
   - Password strength validation (minimum 8 characters)
   - Location: `frontend/src/app/auth/reset-password/page.tsx`

3. **Login Page Update**
   - Added "Forgot Password?" link
   - Location: `frontend/src/components/auth/login-form.tsx`

## How to Use

### For Users

1. **Request Password Reset**
   - Go to the login page
   - Click "Forgot password?" link
   - Enter your email address
   - Click "Send Reset Link"
   - Check your email for the reset link

2. **Reset Password**
   - Click the reset link in your email
   - Enter your new password (minimum 8 characters)
   - Confirm your new password
   - Click "Reset Password"
   - You'll be redirected to the login page

### For Developers

#### Database Migration

The password reset fields are automatically created when the backend starts using SQLModel's `create_all()` method. If you need to manually apply the migration:

```bash
# Connect to your PostgreSQL database
psql -U postgres -d fbr_invoice_portal

# Run the migration
\i backend/migrations/add_password_reset_fields.sql
```

Or use the SQL directly:
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255) NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP NULL;
CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(reset_token);
```

#### Email Configuration (Production)

The current implementation logs reset links to the console. For production, update the `send_reset_email` method in `backend/src/services/password_reset_service.py` to use a real email service:

**Option 1: SMTP**
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_reset_email(email: str, token: str, frontend_url: str = "http://localhost:3000") -> bool:
    reset_link = f"{frontend_url}/auth/reset-password?token={token}"

    msg = MIMEMultipart()
    msg['From'] = "noreply@yourcompany.com"
    msg['To'] = email
    msg['Subject'] = "Password Reset Request"

    body = f"""
    Hello,

    You requested a password reset. Click the link below to reset your password:

    {reset_link}

    This link will expire in 1 hour.

    If you didn't request this, please ignore this email.
    """

    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login("your_email@gmail.com", "your_password")
    server.send_message(msg)
    server.quit()

    return True
```

**Option 2: SendGrid**
```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_reset_email(email: str, token: str, frontend_url: str = "http://localhost:3000") -> bool:
    reset_link = f"{frontend_url}/auth/reset-password?token={token}"

    message = Mail(
        from_email='noreply@yourcompany.com',
        to_emails=email,
        subject='Password Reset Request',
        html_content=f'''
        <p>Hello,</p>
        <p>You requested a password reset. Click the link below to reset your password:</p>
        <p><a href="{reset_link}">Reset Password</a></p>
        <p>This link will expire in 1 hour.</p>
        <p>If you didn't request this, please ignore this email.</p>
        '''
    )

    sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    sg.send(message)

    return True
```

## Testing

### Manual Testing

1. **Test Password Reset Request**
   ```bash
   curl -X POST http://localhost:8001/api/v1/password-reset/request \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com"}'
   ```

2. **Check Console Output**
   - Look for the reset link in the backend console
   - Copy the token from the URL

3. **Test Token Verification**
   ```bash
   curl -X POST http://localhost:8001/api/v1/password-reset/verify \
     -H "Content-Type: application/json" \
     -d '{"token": "your_token_here"}'
   ```

4. **Test Password Reset**
   ```bash
   curl -X POST http://localhost:8001/api/v1/password-reset/confirm \
     -H "Content-Type: application/json" \
     -d '{"token": "your_token_here", "new_password": "newpassword123"}'
   ```

### Frontend Testing

1. Navigate to `http://localhost:3000/auth/login`
2. Click "Forgot password?"
3. Enter a registered email address
4. Check the backend console for the reset link
5. Copy the reset link and paste it in your browser
6. Enter a new password and confirm
7. Try logging in with the new password

## Security Features

1. **Secure Token Generation**
   - Uses `secrets.token_urlsafe(32)` for cryptographically secure tokens
   - 32-byte tokens provide 256 bits of entropy

2. **Token Expiration**
   - Tokens expire after 1 hour
   - Expired tokens are automatically rejected

3. **One-Time Use**
   - Tokens are cleared after successful password reset
   - Cannot be reused

4. **Password Validation**
   - Minimum 8 characters required
   - Passwords are hashed using bcrypt

5. **Email Privacy**
   - Generic success message regardless of email existence
   - Prevents email enumeration attacks

## API Documentation

### Request Password Reset
```
POST /api/v1/password-reset/request
Content-Type: application/json

{
  "email": "user@example.com"
}

Response:
{
  "success": true,
  "message": "If an account exists with this email, a password reset link has been sent."
}
```

### Verify Reset Token
```
POST /api/v1/password-reset/verify
Content-Type: application/json

{
  "token": "reset_token_here"
}

Response:
{
  "success": true,
  "message": "Token is valid"
}
```

### Confirm Password Reset
```
POST /api/v1/password-reset/confirm
Content-Type: application/json

{
  "token": "reset_token_here",
  "new_password": "newpassword123"
}

Response:
{
  "success": true,
  "message": "Password has been reset successfully"
}
```

## Troubleshooting

### Issue: Reset link not working
- Check if the token has expired (1 hour limit)
- Verify the token in the URL is complete and not truncated
- Check backend logs for errors

### Issue: Email not received
- In development, check the backend console for the reset link
- In production, verify email service configuration
- Check spam folder

### Issue: Database migration failed
- Ensure PostgreSQL is running
- Check database connection settings
- Manually run the migration SQL commands

## Future Enhancements

1. **Email Templates**
   - HTML email templates with branding
   - Responsive design for mobile devices

2. **Rate Limiting**
   - Limit password reset requests per email
   - Prevent abuse and spam

3. **Multi-Factor Authentication**
   - Additional security layer for password resets
   - SMS or authenticator app verification

4. **Password History**
   - Prevent reuse of recent passwords
   - Track password change history

5. **Account Recovery Options**
   - Security questions
   - Alternative email addresses
   - Phone number verification
