import os
from django.db.models.signals import post_delete,post_save,pre_save,post_init
from django.dispatch import receiver
from .models import Profile,User,management_Profile
from .filters import get_role_object
from django.http import JsonResponse

@receiver(post_delete, sender=Profile)
def delete_profile_photo(sender, instance:Profile, **kwargs):
    if instance.Photo_link:
        if os.path.isfile(instance.Photo_link.path):
            os.remove(instance.Photo_link.path)

@receiver(post_save, sender=Profile)
def create_emp_profile(sender, instance: Profile, created, **kwargs):
    if created and instance.Role.role_name=="MD":
        instance.Employee_id.is_superuser=True
        instance.Employee_id.save()
        management_Profile.objects.create(Employee=instance.Employee_id,Role=instance.Role,Email_id=instance.Email_id,Photo_link=instance.Photo_link,
                                        Date_of_join=instance.Date_of_join,Date_of_birth=instance.Date_of_birth,
                                        Name=instance.Name)
    role_object=instance.Role
    role_object.total_count+=1
    role_object.save()

@receiver(post_save, sender=User)
def create_profile_from_user(sender, instance: User, created, **kwargs):
    try:
        if created and instance.is_superuser:
            role_object=get_role_object(role="Admin")
            role_object.total_count+=1
            management_Profile.objects.create(Employee=instance,Role=role_object,Email_id=instance.email)
            role_object.save()
    except Exception as e:
        print(e)
        return JsonResponse({"Error occured"},status=404)
        