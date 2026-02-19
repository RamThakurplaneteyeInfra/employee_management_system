from django.core.management.base import BaseCommand
from accounts.models import *
from notifications.models import *
from events.models import Holiday
from datetime import date
class Command(BaseCommand):
    help = "add entries to database"

    def handle(self, *args, **kwargs):
        
        # Departments.objects.create(dept_name="None")
        # Functions.objects.create(function="None")
        # Designation.objects.create(designation="GIS")
        # Designation.objects.filter(designation="Designer Engineer").update(designation="Design Engineer")
        # Branch.objects.create(branch_name="None")
        # Use: python manage.py seed_notification_types
        
        # for i in ["NPD","MMR","RG","HC","IP"]:
        #     Functions.objects.create(function=i)
        
        # obj=Quaters.create_quater(quater="Q3",starting_month=9,ending_month=12)
        # Financial_years_Quaters_Mapping.add_quaterwise_year(quater=obj,financial_year_start=2026,financial_year_end=2027)
        ...