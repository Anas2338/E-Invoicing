"""
Email utility functions for sending notifications.
"""
from src.config.settings import settings


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
    # Get admin email from settings
    admin_email = getattr(settings, 'admin_email', 'admin@company.com')

    # In production, use proper email service (SMTP, SendGrid, AWS SES, etc.)
    # For now, log to console
    print(f"\n{'='*60}")
    print(f"NEW USER REGISTRATION - ADMIN NOTIFICATION")
    print(f"{'='*60}")
    print(f"To: {admin_email}")
    print(f"Subject: New User Registration Pending Approval")
    print(f"\nUser Details:")
    print(f"  Name: {user_name}")
    print(f"  Email: {user_email}")
    print(f"  User ID: {user_id}")
    print(f"\nAction Required:")
    print(f"  Please log in to the admin panel to approve or reject this user.")
    print(f"  Admin Panel: http://localhost:3000/admin/users")
    print(f"{'='*60}\n")

    # TODO: Implement actual email sending
    # Example with SMTP:
    # import smtplib
    # from email.mime.text import MIMEText
    # msg = MIMEText(f"New user {user_name} ({user_email}) has registered...")
    # msg['Subject'] = 'New User Registration Pending Approval'
    # msg['From'] = settings.smtp_from_email
    # msg['To'] = admin_email
    # with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
    #     server.send_message(msg)

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
    print(f"\n{'='*60}")
    print(f"ACCOUNT APPROVED - USER NOTIFICATION")
    print(f"{'='*60}")
    print(f"To: {user_email}")
    print(f"Subject: Your Account Has Been Approved")
    print(f"\nHello {user_name},")
    print(f"\nYour account has been approved by the administrator.")
    print(f"You can now log in to the system at: http://localhost:3000/login")
    print(f"\nThank you for registering!")
    print(f"{'='*60}\n")

    # TODO: Implement actual email sending

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
    print(f"\n{'='*60}")
    print(f"ACCOUNT REJECTED - USER NOTIFICATION")
    print(f"{'='*60}")
    print(f"To: {user_email}")
    print(f"Subject: Account Registration Update")
    print(f"\nHello {user_name},")
    print(f"\nWe regret to inform you that your account registration has been declined.")
    if reason:
        print(f"\nReason: {reason}")
    print(f"\nIf you believe this is an error, please contact support.")
    print(f"{'='*60}\n")

    # TODO: Implement actual email sending

    return True
