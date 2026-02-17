from django.core.management.base import BaseCommand
from accounts.models import *
from notifications.models import *
class Command(BaseCommand):
    help = "add entries to database"

    def handle(self, *args, **kwargs):
        
        # Departments.objects.create(dept_name="None")
        # Functions.objects.create(function="None")
        # Designation.objects.create(designation="GIS")
        # Designation.objects.create(designation="DevOPS")
        # Designation.objects.create(designation="Frontend Developer")
        # Designation.objects.create(designation="Marketing and Sales Executive")
        # Designation.objects.create(designation="Full Stack Developer")
        # Designation.objects.filter(designation="Designer Engineer").update(designation="Design Engineer")
        # Roles.objects.get(role_id=8).delete()
        # Branch.objects.create(branch_name="None")
        # User.objects.filter(username="20011").update(username="200011")
        # User.objects.filter(username="5001").update(username="50001")
        # User.objects.filter(username="5001").update(username="50001")
        # User.objects.filter(username="5001").update(username="50001")
        # User.objects.filter(username="5001").update(username="50001")
        # User.objects.filter(username="5001").update(username="50001")
        # User.objects.filter(username="5001").update(username="50001")
        # User.objects.filter(username="5001").update(username="50001")
        # User.objects.filter(username="5001").update(username="50001")
        # User.objects.filter(username="5001").update(username="50001")
        # User.objects.filter(username="5001").update(username="50001")
        # notification_type.objects.create(type_name="Group_message")
        # notification_type.objects.create(type_name="private_message")
        # notification_type.objects.create(type_name="Task_message")
        # notification_type.objects.create(type_name="Group_Created")
        # notification_type.objects.create(type_name="Task_Created")
        
        # for i in ["NPD","MMR","RG","HC","IP"]:
        #     Functions.objects.create(function=i)
        
        # obj=Quaters.create_quater(quater="Q3",starting_month=9,ending_month=12)
        # Financial_years_Quaters_Mapping.add_quaterwise_year(quater=obj,financial_year_start=2026,financial_year_end=2027)
        ...