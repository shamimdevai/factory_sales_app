"""
All timestamps are stored in the DB as naive UTC (datetime.utcnow()), which is
correct practice for storage — but they must be converted to local time for
display, otherwise invoices/dashboards show a time 6 hours behind Bangladesh.
"""
from datetime import datetime, timedelta

LOCAL_UTC_OFFSET_HOURS = 6  # Bangladesh Standard Time (UTC+6, no DST)


def to_local_str(dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    if dt is None:
        return ""
    return (dt + timedelta(hours=LOCAL_UTC_OFFSET_HOURS)).strftime(fmt)