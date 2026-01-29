from ems.RequiredImports import *
from .models import *

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

def get_current_financial_year(input_date:date|None=None):
    if not input_date:
        input_date = date.today()
    year = input_date.year
    month = input_date.month
    
    if month >= 4:
        financial_year = f"{year}-{year + 1}"
    else:
        financial_year = f"{year - 1}-{year}"
    return financial_year
    
def get_quater_object(quater:str):
    if quater:
        obj=Quaters.objects.filter(quater=quater).first()
        return obj
    return None

def get_department_object(dept:str):
    if dept:
        obj=Departments.objects.filter(dept_name=dept).first()
        return obj
    return None

def get_month_quater_object(month:str,quater:str,department:str):
    quater_obj=get_quater_object(quater=quater)
    month=reversed_quater_month[quater][month]
    department_obj=get_department_object(dept=department)
    try:
        obj=Monthly_department_head_and_subhead.objects.filter(department=department_obj,quater=quater_obj,month_of_the_quater=month).first()
        return obj
    except Monthly_department_head_and_subhead.DoesNotExist as e:
        print(e)
        return None

def get_financial_year_details():
    input_date = date.today()
    year = input_date.year
    month = input_date.month
    day=input_date.day
    
    financial_year=get_current_financial_year(input_date=input_date)

    if month in (4, 5, 6):
        quarter = "Q1"
    elif month in (7, 8, 9):
        quarter = "Q2"
    elif month in (10, 11, 12):
        quarter = "Q3"
    else:
        quarter = "Q4"

    quarter_month=quarter_months[quarter][month]
    quarter_month_reversed=reversed_quater_month[quarter][quarter_month]
    print(quarter_month,quarter_month_reversed)

    return {
        "financial_year": financial_year,
        "quarter": quarter,
        "respective_quarter_months": quarter_month,
        "reverse_quater_month":quarter_month_reversed
    }

def get_addeded_entries(request:HttpRequest,**argu):
        try:
            # print(argu)
            month=argu.get("month",None)
            quater=argu.get("quater",None)
            department=argu.get("department",None)
            # print(month,quater,department)
            if month and quater and department:
                month_and_quater_obj=get_month_quater_object(month=month,quater=quater,department=department)
            else:
                raise ValueError("Insuffiecient query data")
            username=argu.get("username")
            date=argu.get("date",None)
            user_obj=get_object_or_404(User,username=username)
            
            # Role-based filtering
            if user_obj and month_and_quater_obj:
                entries = UsersEntries.objects.select_related("user", "month_and_quater_id","status").filter(user=user_obj,month_and_quater_id=month_and_quater_obj).order_by("date")
            elif user_obj and date and month_and_quater_obj:
                entries = UsersEntries.objects.select_related("user", "month_and_quater_id","status").filter(user=user_obj,month_and_quater_id=month_and_quater_obj,date=date).order_by("date")
            else:
                return JsonResponse({"error": "invalid query parameter"}, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
            data = []
            for entry in entries:
                data.append({
                    "id":entry.id,
                    "note":entry.note,
                    "meeting_head": entry.month_and_quater_id.Meeting_head,
                    "meeting_sub_head": entry.month_and_quater_id.meeting_sub_head,
                    "username": entry.user.username,
                    "date": entry.date,
                    "status": entry.status.status_name,
                    "month_quater_id": entry.month_and_quater_id.quater.quater,
                })
            return data
        except ValueError as e:
            print(e)
            return JsonResponse({"error": "query parameter is absent"}, status=404)
        except Http404 as e:
            print(e)
            return JsonResponse({"error": "User profile not found"}, status=404)
        except Exception as e:
            print(e)
            return JsonResponse({"error": str(e)}, status=500)
        
def has_user_entries_seen_access():
    ...