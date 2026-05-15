from django.db import models


class Asset(models.Model):
    class AssetType(models.TextChoices):
        HARDWARE = "hardware", "Hardware"
        SOFTWARE = "software", "Software"

    asset_name = models.CharField(max_length=200)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    asset_type = models.CharField(max_length=20, choices=AssetType.choices)
    assigned_to = models.CharField(max_length=200)
    location = models.CharField(max_length=200, default="", blank=True)
    purpose = models.CharField(max_length=300, default="", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.asset_name
