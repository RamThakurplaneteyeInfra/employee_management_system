from django.db import models

MODULE_CHOICES = [
    ("boq", "BOQ Physical"),
    ("lidar", "LiDAR"),
    ("sar", "SAR"),
]


class RouteCorridorGroup(models.Model):
    """One row per distinct route/corridor name within a module (matched by case-insensitive key)."""

    module = models.CharField(max_length=20, choices=MODULE_CHOICES)
    route_key = models.CharField(max_length=200, db_index=True)
    route_label = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["module", "route_key"],
                name="infra_routegroup_module_routekey_uniq",
            )
        ]
        ordering = ["route_label"]

    def __str__(self):
        return f"{self.module} | {self.route_label}"


class ProjectCatalog(models.Model):
    """Saved project names shown in the top selector."""

    name = models.CharField(max_length=160, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class AbstractStructureEntry(models.Model):
    """Shared field definitions; each module has its own concrete table."""

    INSPECTION_NOT_SET = ""
    INSPECTION_COMPLETED = "Completed"
    INSPECTION_MISSING = "Missing"
    INSPECTION_IN_PROGRESS = "In progress"
    INSPECTION_ISSUE_ATTENTION = "Issue-attention"
    INSPECTION_STATUS_CHOICES = [
        (INSPECTION_NOT_SET, "Not set"),
        (INSPECTION_COMPLETED, "Completed"),
        (INSPECTION_MISSING, "Missing"),
        (INSPECTION_IN_PROGRESS, "In progress"),
        (INSPECTION_ISSUE_ATTENTION, "Issue-attention"),
    ]

    route_group = models.ForeignKey(
        RouteCorridorGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_related",
    )
    project_name = models.CharField(max_length=160, blank=True, default="")
    team_lead_name = models.CharField(max_length=120, blank=True, default="")
    branch = models.CharField(max_length=80, blank=True, default="INFRA_CORE")
    date_of_entry = models.DateField(null=True, blank=True)
    route_corridor = models.CharField(max_length=200, blank=True)

    sr_no = models.CharField(max_length=40, blank=True)
    chainage = models.CharField(max_length=120, blank=True, default="")
    structure_type = models.CharField(max_length=100, blank=True, default="")
    length_of_structure = models.CharField(max_length=120, blank=True)
    span_arrangement = models.CharField(max_length=200, blank=True)
    equipment_notes = models.TextField(blank=True)
    inspection_status = models.CharField(
        max_length=20,
        choices=INSPECTION_STATUS_CHOICES,
        blank=True,
        default="",
    )
    remark = models.TextField(blank=True)

    las_file_submitted = models.BooleanField(default=False)
    reports_available_on_bms_for_las = models.BooleanField(default=False)
    sar_files_submitted = models.BooleanField(default=False)
    reports_available_on_bms_for_sar = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["date_of_entry"]),
            models.Index(fields=["route_group"]),
        ]

    def __str__(self):
        ch = self.chainage or "-"
        dt = self.date_of_entry or "-"
        return f"{ch} | {dt}"


class BoqStructureEntry(AbstractStructureEntry):
    """BOQ Physical form rows."""

    class Meta(AbstractStructureEntry.Meta):
        abstract = False
        verbose_name = "BOQ structure entry"


class LidarStructureEntry(AbstractStructureEntry):
    """LiDAR form rows."""

    class Meta(AbstractStructureEntry.Meta):
        abstract = False
        verbose_name = "LiDAR structure entry"


class SarStructureEntry(AbstractStructureEntry):
    """SAR form rows."""

    class Meta(AbstractStructureEntry.Meta):
        abstract = False
        verbose_name = "SAR structure entry"
