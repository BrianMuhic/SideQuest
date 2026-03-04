from dataclasses import dataclass, field
from datetime import (
    date,
    datetime,
    time,
)
from typing import (
    Any,
)
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config import config
from constant import (
    LOCAL_ZONEINFO,
    UTC_ZONEINFO,
)
from core.db.engine import db_session
from core.models.setting import Setting
from core.service.logger import get_logger
from core.util.date import tz_offset_aware

log = get_logger()

DEFAULT_DATE = date(1900, 1, 1)
DEFAULT_DATETIME = datetime(1900, 1, 1, 0, tzinfo=UTC_ZONEINFO)
DEFAULT_TIME = time(0, 0, 0)


# ============================== Settings ============================== #

# Simulation
SIMULATED_DATE = "SIMULATED_DATE"
SIMULATED_TIME = "SIMULATED_TIME"
USE_SIMULATED_DATE = "USE_SIMULATED_DATE"
USE_SIMULATED_TIME = "USE_SIMULATED_TIME"

EMAIL_REDIRECT_RECIPIENTS = "EMAIL_REDIRECT_RECIPIENTS"


# ============================== Class ============================== #


@dataclass
class _Settings:
    """Application settings loaded from database"""

    modified_date: datetime = DEFAULT_DATETIME

    # Simulation
    use_simulated_date: bool = False
    simulated_date: date = DEFAULT_DATE
    use_simulated_time: bool = False
    simulated_time: time = DEFAULT_TIME

    email_redirect_recipients: list[str] = field(default_factory=list)

    def load(self, db: Session) -> None:
        """Load all settings from database"""

        def _get(name: str, default: Any) -> Any:
            return Setting.get(db, name, default)

        # Simulation - disable in production
        if config.IS_PRODUCTION:
            self.use_simulated_date = self.use_simulated_time = False
        else:
            self.use_simulated_date = _get(USE_SIMULATED_DATE, False)
            self.use_simulated_time = _get(USE_SIMULATED_TIME, False)
        self.simulated_date = date.fromisoformat(_get(SIMULATED_DATE, "1900-01-01"))
        self.simulated_time = time.fromisoformat(_get(SIMULATED_TIME, "00:00:00"))

        self.dev_email_recipients = _get(EMAIL_REDIRECT_RECIPIENTS, [])

    # -------------------- Time -------------------- #

    def set_local_date(self, db: Session, date_: date) -> None:
        """Set simulated date and persist to database"""
        self.simulated_date = date_
        Setting.set(db, SIMULATED_DATE, date_.isoformat())

    def set_local_time(self, db: Session, time_: time) -> None:
        """Set simulated time and persist to database"""
        self.simulated_time = time_
        Setting.set(db, SIMULATED_TIME, time_.isoformat())

    def now(self, tzinfo: ZoneInfo = LOCAL_ZONEINFO) -> datetime:
        """Get the current datetime, respecting simulation settings"""
        if self.use_simulated_date:
            date_ = self.simulated_date
        else:
            date_ = datetime.now(tzinfo).date()

        if self.use_simulated_time:
            time_ = self.simulated_time
        else:
            time_ = datetime.now(tzinfo).time()

        return datetime.combine(date_, time_, tzinfo=tzinfo)

    def now_local(self) -> datetime:
        """Get the current datetime in EST, respecting simulation settings"""
        return self.now(LOCAL_ZONEINFO)

    def now_utc(self) -> datetime:
        """Get the current datetime in UTC, respecting simulation settings"""
        return self.now(UTC_ZONEINFO)

    def today(self, tzinfo: ZoneInfo = LOCAL_ZONEINFO) -> date:
        """Get the current date, respecting simulation settings"""
        return self.now(tzinfo).date()

    def time(self, tzinfo: ZoneInfo = LOCAL_ZONEINFO) -> time:
        """Get the current time, respecting simulation settings"""
        return self.now(tzinfo).time()


# Singleton instance
settings = _Settings()


def load_settings() -> None:
    """
    Load settings from database if database values are more recent.
    Will initialize settings if they are missing.
    """
    with db_session() as db:
        modified = db.scalar(select(func.max(Setting.modified_date)))
        if modified:
            modified = tz_offset_aware(modified)
            if modified > settings.modified_date:
                settings.load(db)
                settings.modified_date = modified
