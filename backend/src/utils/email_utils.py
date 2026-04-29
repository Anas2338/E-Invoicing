"""
Email utility functions for sending notifications.
"""
import resend
from pathlib import Path
from src.config.settings import settings


def send_password_reset_email(email: str, token: str, frontend_url: str = None) -> bool:
    """
    Send password reset email using Resend.

    Args:
        email: User's email address
        token: Reset token
        frontend_url: Frontend URL for reset link (optional, uses settings if not provided)

    Returns:
        True if email was sent successfully, False otherwise
    """
    if not frontend_url:
        frontend_url = settings.frontend_url

    reset_link = f"{frontend_url}/auth/reset-password?token={token}"

    # Configure Resend API key
    if settings.resend_api_key and settings.resend_api_key != "re_your_api_key_here":
        resend.api_key = settings.resend_api_key

        try:
            # Load HTML template
            template_path = Path(__file__).parent.parent / "templates" / "email" / "password_reset.html"
            with open(template_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Replace placeholder with actual reset link
            html_content = html_content.replace("{{reset_link}}", reset_link)

            # Send email via Resend
            params = {
                "from": f"{settings.email_from_name} <{settings.email_from_address}>",
                "to": [email],
                "subject": "Password Reset Request - E-Invoicing Portal",
                "html": html_content,
            }

            response = resend.Emails.send(params)
            print(f"[SUCCESS] Password reset email sent successfully to {email} (ID: {response.get('id', 'N/A')})")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to send password reset email to {email}: {str(e)}")
            # Fall back to console logging
            print(f"\n{'='*60}")
            print(f"PASSWORD RESET EMAIL (FALLBACK - EMAIL SEND FAILED)")
            print(f"{'='*60}")
            print(f"To: {email}")
            print(f"Reset Link: {reset_link}")
            print(f"{'='*60}\n")
            return False
    else:
        # No API key configured - log to console
        print(f"\n{'='*60}")
        print(f"PASSWORD RESET EMAIL (CONSOLE ONLY - NO API KEY)")
        print(f"{'='*60}")
        print(f"To: {email}")
        print(f"Reset Link: {reset_link}")
        print(f"{'='*60}\n")
        return True


def send_admin_notification_email(user_email: str, user_name: str, user_id: str) -> bool:
    """
    Send notification to admin when a new user registers.

    Args:
        user_email: New user's email
        user_name: New user's name
        user_id: New user's ID

    Returns:
        True if notification was sent successfully
    """
    admin_email = getattr(settings, 'admin_email', 'admin@company.com')
    admin_panel_url = f"{settings.frontend_url}/admin/users"

    if settings.resend_api_key and settings.resend_api_key != "re_your_api_key_here":
        resend.api_key = settings.resend_api_key

        try:
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #2563eb;">New User Registration</h2>
                <p>A new user has registered and is pending approval:</p>
                <div style="background-color: #f3f4f6; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Name:</strong> {user_name}</p>
                    <p><strong>Email:</strong> {user_email}</p>
                    <p><strong>User ID:</strong> {user_id}</p>
                </div>
                <p><strong>Action Required:</strong></p>
                <p>Please log in to the admin panel to approve or reject this user.</p>
                <a href="{admin_panel_url}" style="display: inline-block; padding: 12px 24px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0;">Go to Admin Panel</a>
            </body>
            </html>
            """

            params = {
                "from": f"{settings.email_from_name} <{settings.email_from_address}>",
                "to": [admin_email],
                "subject": "New User Registration Pending Approval",
                "html": html_content,
            }

            response = resend.Emails.send(params)
            print(f"[SUCCESS] Admin notification sent successfully (ID: {response.get('id', 'N/A')})")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to send admin notification: {str(e)}")
            return False
    else:
        print(f"\n{'='*60}")
        print(f"NEW USER REGISTRATION - ADMIN NOTIFICATION (CONSOLE ONLY)")
        print(f"{'='*60}")
        print(f"To: {admin_email}")
        print(f"User: {user_name} ({user_email})")
        print(f"Admin Panel: {admin_panel_url}")
        print(f"{'='*60}\n")
        return True


def send_approval_email(user_email: str, user_name: str) -> bool:
    """
    Send notification to user when their account is approved.

    Args:
        user_email: User's email
        user_name: User's name

    Returns:
        True if email was sent successfully
    """
    login_url = f"{settings.frontend_url}/login"

    if settings.resend_api_key and settings.resend_api_key != "re_your_api_key_here":
        resend.api_key = settings.resend_api_key

        try:
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #10b981;">Account Approved! 🎉</h2>
                <p>Hello {user_name},</p>
                <p>Great news! Your account has been approved by the administrator.</p>
                <p>You can now log in to the E-Invoicing Portal and start managing your invoices.</p>
                <a href="{login_url}" style="display: inline-block; padding: 12px 24px; background-color: #10b981; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0;">Log In Now</a>
                <p>If you have any questions, please don't hesitate to contact our support team.</p>
                <p>Thank you for registering!</p>
            </body>
            </html>
            """

            params = {
                "from": f"{settings.email_from_name} <{settings.email_from_address}>",
                "to": [user_email],
                "subject": "Your Account Has Been Approved - E-Invoicing Portal",
                "html": html_content,
            }

            response = resend.Emails.send(params)
            print(f"[SUCCESS] Approval email sent to {user_email} (ID: {response.get('id', 'N/A')})")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to send approval email to {user_email}: {str(e)}")
            return False
    else:
        print(f"\n{'='*60}")
        print(f"ACCOUNT APPROVED - USER NOTIFICATION (CONSOLE ONLY)")
        print(f"{'='*60}")
        print(f"To: {user_email}")
        print(f"User: {user_name}")
        print(f"Login URL: {login_url}")
        print(f"{'='*60}\n")
        return True


def send_rejection_email(user_email: str, user_name: str, reason: str = None) -> bool:
    """
    Send notification to user when their account is rejected.

    Args:
        user_email: User's email
        user_name: User's name
        reason: Rejection reason (optional)

    Returns:
        True if email was sent successfully
    """
    if settings.resend_api_key and settings.resend_api_key != "re_your_api_key_here":
        resend.api_key = settings.resend_api_key

        try:
            reason_html = f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""

            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #ef4444;">Account Registration Update</h2>
                <p>Hello {user_name},</p>
                <p>We regret to inform you that your account registration for the E-Invoicing Portal has been declined.</p>
                {reason_html}
                <p>If you believe this is an error or have questions, please contact our support team.</p>
                <p>Thank you for your understanding.</p>
            </body>
            </html>
            """

            params = {
                "from": f"{settings.email_from_name} <{settings.email_from_address}>",
                "to": [user_email],
                "subject": "Account Registration Update - E-Invoicing Portal",
                "html": html_content,
            }

            response = resend.Emails.send(params)
            print(f"[SUCCESS] Rejection email sent to {user_email} (ID: {response.get('id', 'N/A')})")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to send rejection email to {user_email}: {str(e)}")
            return False
    else:
        print(f"\n{'='*60}")
        print(f"ACCOUNT REJECTED - USER NOTIFICATION (CONSOLE ONLY)")
        print(f"{'='*60}")
        print(f"To: {user_email}")
        print(f"User: {user_name}")
        if reason:
            print(f"Reason: {reason}")
        print(f"{'='*60}\n")
        return True
