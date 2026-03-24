from django.conf import settings
from django.db import models


class CustomerPanelEntry(models.Model):
    """
    Separate customer panel table.
    Isolated from existing Clients models to avoid cross-feature side effects.
    """

    business_name = models.CharField(max_length=255, db_index=True)
    office_address = models.TextField(blank=True, null=True)
    representative_name = models.CharField(max_length=255, blank=True, null=True)
    representative_contact_number = models.CharField(max_length=100, blank=True, null=True)
    serial_no = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    product = models.CharField(max_length=255, blank=True, null=True)
    service = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    value = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    tax_percent = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    total = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_panel_entries",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customer_panel"."entry'
        verbose_name = "customer panel entry"
        verbose_name_plural = "customer panel entries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"], name="cust_panel_created_idx"),
            models.Index(fields=["business_name"], name="cust_panel_business_idx"),
            models.Index(fields=["serial_no"], name="cust_panel_serial_idx"),
        ]

    def __str__(self):
        return self.business_name or str(self.pk)


class CustomerPanelAmountLog(models.Model):
    """
    One-to-many amount/date/notes records linked to a customer panel entry.
    """

    entry = models.ForeignKey(
        CustomerPanelEntry,
        on_delete=models.CASCADE,
        related_name="amount_logs",
        db_column="entry_id",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customer_panel"."amount_log'
        verbose_name = "customer panel amount log"
        verbose_name_plural = "customer panel amount logs"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["entry_id", "-date"], name="cust_panel_log_entry_date_idx"),
        ]

    def __str__(self):
        return f"{self.entry_id} - {self.amount} on {self.date}"

