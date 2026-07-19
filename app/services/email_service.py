"""Email sending service — Member F"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.config import settings


class EmailService:
    """SMTP email sender for password reset, notifications, etc."""

    async def send(self, to_email: str, subject: str, body: str,
                   smtp_host: Optional[str] = None, smtp_port: Optional[int] = None,
                   smtp_user: Optional[str] = None, smtp_password: Optional[str] = None) -> bool:
        host = smtp_host or settings.SMTP_HOST
        port = smtp_port or settings.SMTP_PORT
        user = smtp_user or settings.SMTP_USER
        password = smtp_password or settings.SMTP_PASSWORD

        if not host or not user or not password:
            import logging
            logging.warning("SMTP not configured, skipping email to %s", to_email)
            return False

        msg = MIMEMultipart()
        msg["From"] = user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html", "utf-8"))

        try:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()
            server.login(user, password)
            server.sendmail(user, to_email, msg.as_string())
            server.quit()
            return True
        except Exception:
            import logging
            logging.exception("Email send failed to %s", to_email)
            return False
