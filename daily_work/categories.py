"""
Daily-report fields.

Every employee, intern, and team lead can see and fill every section:
PRODUCTION, PRODUCT DEVELOPMENT, MMR, and SALES.
EMS function codes are stored only as a label on the report.
"""

from __future__ import annotations

UPDATE_KEYS = (
    "production_update",
    "price_value",
    "packaging_user_experience",
    "performance_accuracy",
    "b2c",
    "b2b",
    "gov_semi",
    "cashflow",
    "new_customer",
    "repeat_order",
)

CATEGORY_ORDER = (
    "PRODUCTION",
    "PRODUCT DEVELOPMENT",
    "MMR",
    "SALES",
)

CATEGORY_FIELDS = {
    "PRODUCTION": ("production_update",),
    "PRODUCT DEVELOPMENT": (
        "price_value",
        "packaging_user_experience",
        "performance_accuracy",
    ),
    "MMR": ("b2c", "b2b", "gov_semi"),
    "SALES": ("cashflow", "new_customer", "repeat_order"),
}

FUNCTION_CATEGORIES = {
    "P&S": ("PRODUCTION", "SALES"),
    "PS": ("PRODUCTION", "SALES"),
    "NPD": ("PRODUCT DEVELOPMENT",),
    "NPC": ("PRODUCT DEVELOPMENT",),
    "MMR": ("MMR",),
    "RG": ("MMR",),
}


def empty_updates() -> dict:
    return {key: [] for key in UPDATE_KEYS}


def categories_for_function_names(function_names) -> list[str]:
    found = set()
    for raw in function_names or []:
        code = (raw or "").strip().upper()
        for category in FUNCTION_CATEGORIES.get(code, ()):
            found.add(category)
    return [category for category in CATEGORY_ORDER if category in found]


def categories_for_profile(profile) -> list[str]:
    if profile is None:
        return []
    try:
        names = [
            getattr(function, "function", None)
            for function in profile.functions.all()
        ]
    except Exception:
        names = []
    return categories_for_function_names(names)


def allowed_update_fields(categories: list[str] | None = None) -> list[str]:
    """Every role sees every daily-report field."""
    return list(UPDATE_KEYS)


def reporting_for_profile(profile) -> tuple[str, list[str], bool]:
    """Return (employee_category label, every field key, restricted=False)."""
    categories = categories_for_profile(profile)
    return ", ".join(categories), allowed_update_fields(), False
