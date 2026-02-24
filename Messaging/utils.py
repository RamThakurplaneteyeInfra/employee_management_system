"""
Messaging time helpers: convert DB UTC/GMT to IST for API responses.
"""
from datetime import date, datetime, timezone, timedelta

# Indian Standard Time (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))


def gmt_to_ist(dt):
    """Convert a datetime (UTC/GMT, naive or aware) to IST. Returns None if dt is None. For date-only, returns as-is."""
    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


def gmt_to_ist_str(dt, fmt="%d/%m/%y %H:%M:%S"):
    """Convert UTC datetime to IST and return formatted string. Returns None if dt is None. Handles date-only (DateField)."""
    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.strftime("%d/%m/%y")
    ist = gmt_to_ist(dt)
    return ist.strftime(fmt) if ist else None


def gmt_to_ist_date_str(dt):
    """IST date only: %d/%m/%y."""
    return gmt_to_ist_str(dt, "%d/%m/%y") if dt else None


def gmt_to_ist_time_str(dt):
    """IST time only: %H:%M."""
    return gmt_to_ist_str(dt, "%H:%M") if dt else None
