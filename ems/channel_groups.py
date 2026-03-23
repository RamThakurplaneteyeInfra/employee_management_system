import re
from typing import Any


# Channels group names must be ASCII and contain only:
# alphanumerics, hyphens (-), underscores (_), or periods (.)
# length must be < 100.
_INVALID_GROUP_CHARS_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def _to_ascii_str(value: Any) -> str:
    """
    Convert value to a safe ASCII string for Channels group names.
    Non-ascii characters are removed (best-effort).
    """
    s = str(value if value is not None else "")
    s = s.strip()
    # Remove non-ascii.
    s = s.encode("ascii", "ignore").decode("ascii")
    return s


def safe_group_suffix(value: Any, fallback: str = "user") -> str:
    """
    Return a sanitized suffix that is valid inside a Channels group name.
    """
    s = _to_ascii_str(value).replace(" ", "_")
    s = _INVALID_GROUP_CHARS_RE.sub("_", s)
    s = s.strip("_.-")
    return s or fallback


def safe_group_name(prefix: str, value: Any, max_len: int = 99) -> str:
    """
    Build a Channels-valid group name like: <prefix><sanitized>.

    Channels requires length < 100, so we cap at 99.
    """
    prefix = _to_ascii_str(prefix)
    suffix = safe_group_suffix(value, fallback="anon")

    # Ensure allowed charset for the final name too.
    prefix = _INVALID_GROUP_CHARS_RE.sub("_", prefix)
    name = f"{prefix}{suffix}"
    if len(name) <= max_len:
        return name

    # Truncate suffix to fit the prefix.
    allowed_suffix_len = max_len - len(prefix)
    if allowed_suffix_len <= 0:
        return prefix[:max_len]
    return f"{prefix}{suffix[:allowed_suffix_len]}"


def user_group_name(username: Any) -> str:
    return safe_group_name("user_", username)


def call_group_name(username: Any) -> str:
    return safe_group_name("call_", username)


def product_group_name(product_label: Any) -> str:
    return safe_group_name("notifications_product_", product_label)


def group_call_group_name(call_id: Any) -> str:
    # call_id is numeric in your code; still sanitize to be safe.
    try:
        call_id_int = int(call_id)
    except (TypeError, ValueError):
        call_id_int = 0
    return safe_group_name("group_call_", call_id_int)

