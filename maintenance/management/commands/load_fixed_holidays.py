
# from django.core.management.base import BaseCommand
# from events.models import Holiday


# COMPANY_NAME_MAP = {
#     "Maharashtra Day": "Maharashtra / Labour Day",
#     "Independence Day": "Independence Day",
#     "Ganesh Chaturthi": "Ganesh Chaturthi",
#     "Gandhi Jayanti": "Mahatma Gandhi Jayanti",
#     "Naraka Chaturdasi": "Deepawali – Narak Chaturdashi",
#     "Lakshmi Puja": "Deepawali – Laxmi Poojan",
#     "Republic Day": "Republic Day",
#     "Holi": "Holi",
#     "Gudi Padwa": "Gudhi Padwa",
# }


# class Command(BaseCommand):
#     help = "Load company-approved FIXED holidays"

#     def add_arguments(self, parser):
#         parser.add_argument("start_year", type=int)
#         parser.add_argument("end_year", type=int)

#     def handle(self, *args, **options):
#         for year in range(options["start_year"], options["end_year"] + 1):
#             mh_holidays = holidays.IN(years=year, prov="MH")

#             for holiday_date, name in mh_holidays.items():
#                 for keyword, company_name in COMPANY_NAME_MAP.items():
#                     if keyword.lower() in name.lower():
#                         Holiday.objects.update_or_create(
#                             date=holiday_date,
#                             defaults={
#                                 "name": company_name,
#                                 "holiday_type": Holiday.FIXED,
#                             },
#                         )

#         self.stdout.write(
#             self.style.SUCCESS("✅ Fixed company holidays synced successfully")
#         )
