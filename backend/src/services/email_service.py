import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import settings

logger = logging.getLogger(__name__)


def _create_reset_pin_email(to_email: str, pin: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your Password Reset Code"
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email

    html = f"""\
<html>
<body style="font-family: Arial, sans-serif; background-color: #f6f6f7; padding: 40px 0; margin: 0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e1e3e5;">
    <tr>
      <td style="padding: 32px 40px 24px; text-align: center;">
        <h2 style="color: #202223; margin: 0; font-size: 20px;">Password Reset Code</h2>
      </td>
    </tr>
    <tr>
      <td style="padding: 0 40px 8px; text-align: center;">
        <p style="color: #6d7175; font-size: 14px; margin: 0;">Use the 6-digit code below to reset your password. This code expires in <strong>10 minutes</strong>.</p>
      </td>
    </tr>
    <tr>
      <td style="padding: 24px 40px; text-align: center;">
        <div style="background: #f1f8f5; border-radius: 8px; padding: 20px; border: 1px solid #d1fae5;">
          <span style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #008060; font-family: 'Courier New', monospace;">{pin}</span>
        </div>
      </td>
    </tr>
    <tr>
      <td style="padding: 8px 40px 24px; text-align: center;">
        <p style="color: #8c9196; font-size: 12px; margin: 0;">If you did not request this code, you can safely ignore this email.</p>
      </td>
    </tr>
    <tr>
      <td style="padding: 16px 40px; background: #fafafa; border-top: 1px solid #f0f0f0; text-align: center;">
        <p style="color: #c0c0c0; font-size: 11px; margin: 0;">E-Invoicing Portal</p>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    msg.attach(MIMEText(html, "html"))
    return msg


def send_reset_pin_email(to_email: str, pin: str) -> bool:
    """Send a password reset PIN email via SMTP. Returns True on success."""
    try:
        msg = _create_reset_pin_email(to_email, pin)

        if settings.smtp_use_tls:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15)

        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)

        server.send_message(msg)
        server.quit()

        logger.info(f"Reset PIN email sent to {to_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(f"SMTP authentication failed for {settings.smtp_username}. Check SMTP_USERNAME and SMTP_PASSWORD.")
        raise
    except smtplib.SMTPConnectError:
        logger.error(f"SMTP connection failed to {settings.smtp_host}:{settings.smtp_port}. Check SMTP_HOST and SMTP_PORT.")
        raise
    except Exception as e:
        logger.error(f"Failed to send reset PIN email to {to_email}: {type(e).__name__}: {e}")
        raise
