from django.db import models
from accounts.models import User

# Create your models here.
class notification_type(models.Model):
    type_name=models.CharField(verbose_name="notification_type_name", max_length=50)
    class Meta:
        db_table='notifications"."types'
    
class Notification(models.Model):
    type_of_notification=models.ForeignKey(notification_type,on_delete=models.CASCADE)
    from_user=models.ForeignKey(User,on_delete=models.CASCADE,to_field="username",related_name="notification_sender")
    receipient= models.ForeignKey(User, on_delete=models.CASCADE,to_field="username",related_name="notification_receiver")
    message = models.TextField(max_length=100)
    is_read = models.BooleanField(default=False)
    # is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table='notifications"."Notification'
        ordering=["created_at"]

    def __str__(self):
        return self.message
