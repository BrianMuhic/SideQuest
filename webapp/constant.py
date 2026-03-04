from zoneinfo import ZoneInfo

from config import config

LOCAL_ZONEINFO = ZoneInfo(config.LOCAL_TIMEZONE)
UTC_ZONEINFO = ZoneInfo("UTC")
