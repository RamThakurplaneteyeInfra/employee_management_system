from django.contrib import admin
from .models import Product, Project, ProjectParticipant

# Register your models here.
admin.site.register(Product)
admin.site.register(Project)
admin.site.register(ProjectParticipant)
