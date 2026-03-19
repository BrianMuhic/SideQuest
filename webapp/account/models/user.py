from typing import Self

from flask_login import UserMixin
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

from core.db.base_enum import BaseEnum
from core.db.base_model import BaseAudit
from core.db.mapped_types import (
    DateTimeNone,
    IntZero,
    Str,
    StrNone,
)

HASHING_METHOD = "pbkdf2:sha256:100000"


class Role(BaseEnum):
    ADMIN = 1
    USER = 2


class User(BaseAudit, UserMixin):
    __tablename__ = "users"

    username: Str = mapped_column(index=True, unique=True)
    role: Mapped[Role] = mapped_column(default=Role.USER)

    _password: Str
    access_token: StrNone = mapped_column(String(32), unique=True)
    last_login_at: DateTimeNone
    num_logins: IntZero

    # -------------------- Authentication -------------------- #

    def set_password(self, plain_password: str) -> None:
        self._password = generate_password_hash(plain_password, method=HASHING_METHOD)

    def check_password(self, plain_password: str) -> bool:
        return check_password_hash(self._password, plain_password)

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    # -------------------- Other -------------------- #

    def __repr__(self) -> str:
        return f"<User #{self.id} {self.username}>"

    @classmethod
    def with_username(cls, db: Session, username: str) -> Self | None:
        return db.scalar(select(cls).filter_by(username=username))
