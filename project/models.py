from django.db import models
from accounts.models import User
from task_management.models import TaskStatus

# Create your models here.


class Product(models.Model):
    """Product: unique name and description. Same schema pattern as Project (name, description, timestamps)."""
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project"."Product'
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    """Project: name, description, initiator, participants (M2M), status, deadline, and timestamps."""
    # Project status choices
    name = models.CharField(max_length=255,unique=True)
    description = models.TextField(null=True)
    # ForeignKey creates a one-to-many relationship (One initiator per project)
    initiator = models.ForeignKey(User,on_delete=models.CASCADE,related_name='initiated_projects')
    # ManyToManyField allows multiple participants per project and multiple projects per user
    participants = models.ManyToManyField(User,related_name='participating_projects',blank=True,through="ProjectParticipant")
    status = models.ForeignKey(TaskStatus,on_delete=models.CASCADE,null=True,related_name="project_status")
    deadline = models.DateField()
    # Automatically sets the field to now when the object is first created
    created_at = models.DateTimeField(auto_now_add=True)
    # Automatically updates the field to now every time the object is saved
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table='project"."Project'
        verbose_name='Project'
        ordering=["deadline"]
        
    def __str__(self):
        return self.name
    
class ProjectParticipant(models.Model):
    """Through model: user participating in a project; joined_at timestamp."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Enforces uniqueness at the database level
        db_table='project"."ProjectParticipant'
        verbose_name='ProjectParticipant'
        ordering=["project"]
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'user'], 
                name='unique_project_participant'
            )
        ]