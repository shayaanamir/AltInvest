"""
backend/utils/mailer.py

Sends account emails (password reset, email verification) over SMTP when it is configured:

    SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD,
    SMTP_FROM (default SMTP_USER), SMTP_STARTTLS (default "true")

Without SMTP_HOST nothing is sent: the message, including its link, is written to the server log
instead, so local development still works. Never raises; returns whether the email was sent.
"""
import os
import smtplib
import logging
from email.message import EmailMessage

log = logging.getLogger("mailer")


def smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST"))


def send_email(to: str, subject: str, body: str) -> bool:
    host = os.getenv("SMTP_HOST")
    if not host:
        print(f"[mailer] SMTP not configured; email to {to} not sent.\n  Subject: {subject}\n  {body}")
        return False

    user = os.getenv("SMTP_USER")
    msg = EmailMessage()
    msg["From"] = os.getenv("SMTP_FROM") or user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT") or "587"), timeout=15) as smtp:
            if (os.getenv("SMTP_STARTTLS") or "true").lower() != "false":
                smtp.starttls()
            if user:
                smtp.login(user, (os.getenv("SMTP_PASSWORD") or ""))
            smtp.send_message(msg)
        return True
    except Exception as exc:
        log.error("[mailer] sending to %s failed: %s: %s", to, type(exc).__name__, exc)
        return False
