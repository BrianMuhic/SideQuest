import time
from dataclasses import dataclass
from typing import Sequence

from email_validator import EmailNotValidError, validate_email
from flask_mail import (
    Attachment,
    Connection,
    Message,
)
from sqlalchemy import update
from sqlalchemy.orm import Session

from core.app.extensions import mail
from core.models.email_log import EmailLog
from core.service.logger import get_logger
from core.util.date import now_utc

log = get_logger()


MAX_CONNECTION_ATTEMPTS = 3
MAX_EMAIL_ATTEMPTS = 2


@dataclass
class Email:
    sender: str
    recipients: Sequence[str]
    cc: Sequence[str]
    bcc: Sequence[str]
    subject: str
    body: str
    is_html: bool
    attachments: Sequence[Attachment]
    reply_to: str | None

    redirect: bool
    redirect_to: Sequence[str]

    log_id: int


# ==================== Public Methods ==================== #


def send_email(
    db: Session,
    to: Sequence[str],
    subject: str,
    body: str,
    is_html: bool = True,
    sender: str | None = None,
    cc: Sequence[str] = (),
    bcc: Sequence[str] = (),
    attachments: Sequence[Attachment] | Attachment = (),
    reply_to: str | None = None,
) -> int:
    """Generates/validates email, immediately sends or queues email depending on if message batching is enabled."""

    from config import config

    email = _create_email(
        db=db,
        sender=(_clean_emails(sender) or _clean_emails(config.MAIL_DEFAULT_SENDER))[0],  # type: ignore
        recipients=_clean_emails(to),
        cc=_clean_emails(cc),
        bcc=_clean_emails(bcc),
        subject=subject.strip(),
        body=body.strip(),
        is_html=is_html,
        attachments=attachments if isinstance(attachments, Sequence) else [attachments],
        reply_to=_clean_emails(reply_to),
        redirect=config.MAIL_REDIRECT_TO_DEVELOPER,
        redirect_to=_clean_emails(config.MAIL_REDIRECT_RECIPIENTS),
    )

    if _validate_email(email):
        _send_emails(db, email)

    return email.log_id


# ==================== Sending ==================== #


def _send_emails(db: Session, emails: Sequence[Email] | Email) -> None:
    """
    Send one or more emails, handling connection establishment and bulk log updates.

    Skips actual sending if in testing mode or all emails are redirected to nothing.
    Establishes a single mail connection for all emails to minimize overhead.
    If connection fails, marks all emails as failed. Otherwise, attempts to send
    each email individually through the connection.
    """

    from config import config

    if isinstance(emails, Email):
        emails = [emails]

    log_ids = [email.log_id for email in emails]

    # Don't connect to mailgun if testing or all emails are redirected to nothing
    if config.TESTING or all(e.redirect and not e.redirect_to for e in emails):
        db.bulk_update_mappings(
            EmailLog,  # type: ignore
            [
                dict(
                    id=email.log_id,
                    sent_at=now_utc(),
                    failed=False,
                )
                for email in emails
            ],
        )
        log.i(f"Sent email(s) {log_ids}")
        return

    try:
        with _establish_mail_connection() as conn:  # type: ignore
            for email in emails:
                _send_email(db, conn, email)
        log.i(f"Sent email(s) {log_ids}")
    except Exception as e:
        log.e(f"Error '{e}' with mail connection while sending email(s) {log_ids}")
        return


def _send_email(db: Session, conn: Connection, email: Email, attempt: int = 1) -> None:
    """
    Send a single email through an existing connection with retry logic.

    Handles exponential backoff on failure (2^attempt seconds between retries).
    Updates the email log with success/failure status after sending or max attempts.
    Skips sending for redirected emails with no redirect_to addresses.
    """

    def _update_email_log(failed: bool) -> None:
        db.execute(
            update(EmailLog)
            .where(EmailLog.id == email.log_id)
            .values(sent_at=now_utc(), failed=failed)
        )

    if email.redirect and not email.redirect_to:
        _update_email_log(failed=False)
        return

    try:
        message = _build_message(email)
        conn.send(message)
        _update_email_log(failed=False)
        return
    except Exception as e:
        if attempt == MAX_EMAIL_ATTEMPTS:
            log.e(f"Error '{e}' while attempting to send email {email.log_id}")
            _update_email_log(failed=True)
            return
        log.w(e)
        time.sleep(2**attempt)

    _send_email(db, conn, email, attempt + 1)


def _establish_mail_connection(attempt: int = 1) -> Connection:
    """Attempts to establish a connection to mailgun."""

    try:
        return mail.connect()
    except Exception as e:
        if attempt == MAX_CONNECTION_ATTEMPTS:
            raise e
        log.w(e)
        time.sleep(2**attempt)

    return _establish_mail_connection(attempt + 1)


# ==================== Helpers ==================== #


def _create_email(
    db: Session,
    sender: str,
    recipients: Sequence[str],
    cc: Sequence[str],
    bcc: Sequence[str],
    subject: str,
    body: str,
    is_html: bool,
    attachments: Sequence[Attachment],
    reply_to: Sequence[str],
    redirect: bool,
    redirect_to: Sequence[str],
) -> Email:
    """Create an Email and EmailLog."""

    reply = sender if not reply_to else reply_to[0]
    filenames = ",".join(f.filename for f in attachments if f.filename) or None
    redirected_to = ",".join(redirect_to) or None
    email_log = EmailLog(
        sender=sender,
        recipients=",".join(recipients),
        cc=",".join(cc),
        bcc=",".join(bcc),
        subject=subject,
        body=body,
        is_html=is_html,
        attachment_filenames=filenames,
        reply_to=reply,
        redirected=redirect,
        redirected_to=redirected_to if redirect else None,
        sent_at=now_utc(),
        failed=True,
    ).add(db, flush=True)

    email = Email(
        sender=sender,
        recipients=recipients,
        cc=cc,
        bcc=bcc,
        subject=subject,
        body=body,
        is_html=is_html,
        attachments=attachments,
        reply_to=reply,
        redirect=redirect,
        redirect_to=redirect_to,
        log_id=email_log.id,
    )

    return email


def _build_message(email: Email) -> Message:
    """Builds a Message object used to actually send out the email."""
    actual_recipients = email.redirect_to if email.redirect else email.recipients
    actual_cc = [] if email.redirect else email.cc
    actual_bcc = [] if email.redirect else email.bcc

    body = email.body
    if email.redirect:
        line = "<br/>" if email.is_html else "\n"
        redirect_info = f"{line}--- REDIRECTED EMAIL ---{line}"
        redirect_info += f"Original Recipients: {', '.join(email.recipients)}{line}"
        if email.cc:
            redirect_info += f"Original CC: {', '.join(email.cc)}{line}"
        if email.bcc:
            redirect_info += f"Original BCC: {', '.join(email.bcc)}{line}"
        redirect_info += f"{line}------------------------{line * 2}"
        body = redirect_info + body

    message = Message(
        subject=email.subject,
        recipients=actual_recipients,  # type: ignore
        body=body if not email.is_html else None,
        html=body if email.is_html else None,
        sender=email.sender,
        cc=actual_cc,  # type: ignore
        bcc=actual_bcc,  # type: ignore
        attachments=email.attachments,  # type: ignore
        reply_to=email.reply_to,
        extra_headers={"sender": email.sender},
    )

    return message


# ==================== Validation ==================== #


def _clean_emails(emails: Sequence[str] | str | None) -> list[str]:
    """Takes in email(s) and strips out invalid addresses."""
    if not emails:
        return []

    if isinstance(emails, str):
        emails = emails.split(",")

    cleaned_emails = []
    for email in emails:
        parts = [part.strip() for part in email.split(",")]
        cleaned_emails.extend(part for part in parts if part)

    return cleaned_emails


def _validate_email(email: Email) -> bool:
    """Validate all email fields for sendability."""
    invalid = False

    error_prefix = f"(Email #{email.log_id})"

    if len(email.recipients) == 0:
        log.e(f"{error_prefix} At least one recipient is required")
        invalid = True

    if email.subject == "":
        log.e(f"{error_prefix} Subject cannot be empty")
        invalid = True

    if email.body == "":
        log.e(f"{error_prefix} Body cannot be empty")
        invalid = True

    for address in (email.sender, *email.recipients, *email.cc, *email.bcc):
        try:
            validate_email(
                address,
                check_deliverability=False,
                allow_smtputf8=True,
                allow_empty_local=False,
            )
        except EmailNotValidError as err:
            log.e(f"{error_prefix} Invalid email address '{address}': {err}")
            invalid = True

    return not invalid
