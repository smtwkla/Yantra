"""The one place that talks SMTP (S032 § 3, § 5.5): one plain-text email to one recipient,
through the server in the SMTP_* secrets (Mailgun in production), over STARTTLS with the
certificate checked, then a login.

The settings are read from config at call time, not at import: the pytest fixture and the e2e
backend set config.SMTP_* after import.  The email_send handler takes ``send`` as a parameter,
so tests pass a fake instead of connecting anywhere.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage

import config
from company_settings import SMTP_TIMEOUT_SECONDS

log = logging.getLogger(__name__)


def enabled():
    """Email is set up when the host, the port and the sender are all present (S032 U5): a
    missing one means off, never a guessed default."""
    return bool(config.SMTP_HOST and config.SMTP_PORT and config.SMTP_FROM)


def send(to, subject, body):
    """Send one email to ``to``, from SMTP_FROM.  Any failure raises (smtplib's exceptions, an
    OSError for the network); the caller decides with email_core.smtp_outcome."""
    message = EmailMessage()
    message["From"] = config.SMTP_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    smtp = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS)
    try:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
        smtp.send_message(message)
    except BaseException:
        smtp.close()
        raise
    # The server has accepted the message: from here the email counts as sent.  A failure of QUIT
    # must not reach the handler, or a 4xx would resend the email and a 5xx would mark it failed.
    try:
        smtp.quit()
    except (smtplib.SMTPException, OSError) as exc:
        log.warning("SMTP QUIT failed after the message was accepted: %s", type(exc).__name__)
    finally:
        smtp.close()
