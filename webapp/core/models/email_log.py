from core.db.base_model import BaseAudit
from core.db.mapped_types import (
    Bool,
    DateTime,
    Str,
    StrLong,
    StrLongNone,
    StrNone,
    Text,
)


class EmailLog(BaseAudit):
    __tablename__ = "email_logs"

    sender: Str
    recipients: StrLong
    cc: StrLongNone
    bcc: StrLongNone
    subject: Str
    body: Text
    is_html: Bool
    attachment_filenames: StrNone
    reply_to: StrNone

    redirected: Bool
    redirected_to: StrLongNone

    sent_at: DateTime
    failed: Bool
