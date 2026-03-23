"""
Client CRM: stages, profiles, and conversations.
Tables live in clients schema; indexes added for common filters and ordering.
"""
from django.db import models
from django.conf import settings
from project.models import Project


class CurrentClientStage(models.Model):
    """Static pipeline stages: Leads, Qualified, Demo, Proposal, Performer, Invoice, Repeat."""
    name = models.CharField(max_length=50, unique=True, db_index=True)

    class Meta:
        db_table = 'clients"."current_client_stage'
        verbose_name = "current client stage"
        verbose_name_plural = "current client stages"
        ordering = ["name"]

    def __str__(self):
        return self.name


def _get_leads_stage_id():
    """Return pk of stage named 'Leads' for default; None if not yet created."""
    try:
        return CurrentClientStage.objects.get(name="Leads").pk
    except CurrentClientStage.DoesNotExist:
        return None


class ClientProfile(models.Model):
    """Client record: company, contacts, stage, product, and members (M2M via ClientProfileMembers)."""
    company_name = models.CharField(max_length=255, db_index=True)
    client_name = models.CharField(max_length=255)
    client_contact = models.CharField(max_length=100, blank=True)
    representative_contact_number = models.CharField(max_length=100, blank=True)
    representative_name = models.CharField(max_length=255, blank=True)
    motive = models.CharField(max_length=255, blank=True)
    status = models.ForeignKey(
        CurrentClientStage,
        on_delete=models.PROTECT,
        related_name="client_profiles",
        null=True,
        blank=True,
        db_index=True,
        default=_get_leads_stage_id,
    )
    gst_number = models.CharField(max_length=50, blank=True, db_index=True)
    Product = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        related_name="client_profiles",
        null=True,
        blank=True,
        db_index=True,
    )
    product_value = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional numeric value associated with the product (e.g. quote or amount).",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="ClientProfileMembers",
        related_name="client_profiles",
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_client_profiles",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clients"."client_profile'
        verbose_name = "client profile"
        verbose_name_plural = "client profiles"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"], name="client_profile_created_at_idx"),
            models.Index(fields=["company_name"], name="client_profile_company_idx"),
        ]

    def __str__(self):
        return self.company_name or str(self.pk)


class ClientProfileMembers(models.Model):
    """Through model for ClientProfile members (M2M to User)."""
    client_profile = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="member_links",
        db_column="client_profile_id",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_profile_memberships",
        db_column="user_id",
    )

    class Meta:
        db_table = 'clients"."client_profile_members'
        verbose_name = "client profile member"
        verbose_name_plural = "client profile members"
        unique_together = [("client_profile", "user")]
        indexes = [
            models.Index(fields=["client_profile_id"], name="client_members_profile_idx"),
            models.Index(fields=["user_id"], name="client_members_user_idx"),
        ]


class ClientConversation(models.Model):
    """Note attached to a client; created_by and created_at for audit."""
    note = models.TextField()
    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="conversations",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_conversations",
        db_index=True,
    )
    # Interaction channel (e.g. call, email, WhatsApp) for this conversation
    medium = models.ForeignKey(
        "ClientInteractionChannels",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
        db_column="interaction_channel_id",
    )

    class Meta:
        db_table = 'clients"."client_conversation'
        verbose_name = "client conversation"
        verbose_name_plural = "client conversations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client_id", "-created_at"], name="client_conv_client_created_idx"),
        ]

    def __str__(self):
        return f"Conversation {self.pk} for {self.client_id}"


class ClientInteractionChannels(models.Model):
    """Master list of client interaction channels/mediums (e.g. call, email, WhatsApp)."""
    medium = models.CharField(max_length=100)

    class Meta:
        db_table = 'clients"."client_interaction_channels'
        verbose_name = "client interaction channel"
        verbose_name_plural = "client interaction channels"

    def __str__(self):
        return self.medium or str(self.pk)
