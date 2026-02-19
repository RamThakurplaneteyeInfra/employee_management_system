from asgiref.sync import sync_to_async
from ems.RequiredImports import *
from .models import *
from datetime import date

# # # # # #  baseurl="http://localhost:8000" # # # # # # # # # # # #


quarter_months = {
        "Q1": {4:"April", 5:"May", 6:"June"},
        "Q2": {7:"July", 8:"August", 9:"September"},
        "Q3": {10:"October", 11:"November", 12:"December"},
        "Q4": {1:"January", 2:"February", 3:"March"},
    }
    
reversed_quater_month= {
        "Q1": {"April":1, "May":2, "June":3},
        "Q2": {"July":1, "August":2, "September":3},
        "Q3": {"October":1, "November":2,"December":3},
        "Q4": {"January":1, "February":2, "March":3},
    }

# ==================== Pure helpers (no DB) ====================
def get_current_financial_year(input_date: date | None = None):
    if not input_date:
        input_date = date.today()
    year = input_date.year
    month = input_date.month
    
    if month >= 4:
        financial_year = f"{year}-{year + 1}"
    else:
        financial_year = f"{year - 1}-{year}"
    return financial_year
    
# ==================== get_quater_object ====================
def _get_quater_object_sync(quater: str):
    if quater:
        return Quaters.objects.filter(quater=quater).first()
    return None


async def get_quater_object(quater: str):
    return await sync_to_async(_get_quater_object_sync)(quater)


# ==================== get_department_object ====================
def _get_department_object_sync(dept: str):
    if dept:
        return Departments.objects.filter(dept_name=dept).first()
    return None


async def get_department_object(dept: str):
    return await sync_to_async(_get_department_object_sync)(dept)


# ==================== get_month_quater_object ====================
def _get_month_quater_object_sync(month: str, quater: str, department: str):
    quater_obj = _get_quater_object_sync(quater=quater)
    month = reversed_quater_month[quater][month]
    department_obj = _get_department_object_sync(dept=department)
    try:
        return Monthly_department_head_and_subhead.objects.filter(department=department_obj, quater=quater_obj, month_of_the_quater=month).first()
    except Monthly_department_head_and_subhead.DoesNotExist:
        return None


async def get_month_quater_object(month: str, quater: str, department: str):
    return await sync_to_async(_get_month_quater_object_sync)(month, quater, department)


# ==================== get_financial_year_details ====================
def _get_financial_year_details_sync():
    input_date = date.today()
    year = input_date.year
    month = input_date.month

    financial_year = get_current_financial_year(input_date=input_date)

    if month in (4, 5, 6):
        quarter = "Q1"
    elif month in (7, 8, 9):
        quarter = "Q2"
    elif month in (10, 11, 12):
        quarter = "Q3"
    else:
        quarter = "Q4"

    quarter_month = quarter_months[quarter][month]
    quarter_month_reversed = reversed_quater_month[quarter][quarter_month]

    return {
        "financial_year": financial_year,
        "quarter": quarter,
        "respective_quarter_months": quarter_month,
        "reverse_quater_month": quarter_month_reversed
    }


def get_financial_year_details():
    return _get_financial_year_details_sync()


# ==================== get_addeded_entries ====================
def _get_addeded_entries_sync(request: HttpRequest, **argu):
    try:
        month = argu.get("month", None)
        quater = argu.get("quater", None)
        department = argu.get("department", None)
        user_obj = argu.get("user", None)
        date_val = argu.get("date", None)
        if month and quater and department:
            month_and_quater_obj = _get_month_quater_object_sync(month=month, quater=quater, department=department)
        else:
            raise ValueError("Insufficient query data")
        if user_obj and month_and_quater_obj:
            entries = UsersEntries.objects.select_related("user", "month_and_quater_id", "status").filter(user=user_obj, month_and_quater_id=month_and_quater_obj).order_by("date")
        elif user_obj and date_val and month_and_quater_obj:
            entries = UsersEntries.objects.select_related("user", "month_and_quater_id", "status").filter(user=user_obj, month_and_quater_id=month_and_quater_obj, date=date_val).order_by("date")
        else:
            return JsonResponse({"error": "invalid query parameter"}, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
        data = []
        for entry in entries:
            data.append({
                "id": entry.id,
                "note": entry.note,
                "meeting_head": entry.month_and_quater_id.Meeting_head,
                "meeting_sub_head": entry.month_and_quater_id.meeting_sub_head,
                "username": entry.user.username,
                "date": entry.date,
                "status": entry.status.status_name,
                "month_quater_id": entry.month_and_quater_id.quater.quater,
            })
        return data
    except ValueError:
        return JsonResponse({"error": "query parameter is absent"}, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


async def get_addeded_entries(request: HttpRequest, **argu):
    return await sync_to_async(_get_addeded_entries_sync)(request, **argu)