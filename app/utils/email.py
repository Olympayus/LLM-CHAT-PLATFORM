"""邮件发送工具（密码重置等场景）"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.config import settings


async def send_email(
    to_email: str,
    subject: str,
    body: str,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    smtp_user: Optional[str] = None,
    smtp_password: Optional[str] = None,
) -> bool:
    """发送邮件

    Returns:
        bool: 发送成功返回 True，失败返回 False
    """
    host = smtp_host or getattr(settings, "SMTP_HOST", None)
    port = smtp_port or getattr(settings, "SMTP_PORT", 587)
    user = smtp_user or getattr(settings, "SMTP_USER", None)
    password = smtp_password or getattr(settings, "SMTP_PASSWORD", None)

    if not host or not user or not password:
        import logging
        logging.warning("SMTP 未配置，跳过邮件发送")
        return False

    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html", "utf-8"))

    try:
        # TODO: 生产环境使用 aiosmtplib 异步发送
        server = smtplib.SMTP(host, port, timeout=10)
        server.starttls()
        server.login(user, password)
        server.sendmail(user, to_email, msg.as_string())
        server.quit()
        return True
    except Exception:
        import logging
        logging.exception(f"邮件发送失败 to={to_email}")
        return False
