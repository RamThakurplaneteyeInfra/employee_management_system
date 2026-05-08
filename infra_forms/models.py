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
    service = models.JSONField(
        default=list,
        blank=True,
        help_text="Optional list of service values from frontend dropdown(s).",
    )
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


class StructureEntry(models.Model):
    """
    Unified structure entry table.

    One physical row stores data from up to three modules (BOQ, LiDAR, SAR).
    Each module has its own status & remark fields, plus a presence flag
    (`has_boq`, `has_lidar`, `has_sar`) so module-specific list endpoints
    only show rows that the module actually owns.

    The legacy per-module tables (`BoqStructureEntry`, `LidarStructureEntry`,
    `SarStructureEntry`) are kept untouched as a permanent backup and are
    no longer written to by the API.
    """

    INSPECTION_STATUS_CHOICES = AbstractStructureEntry.INSPECTION_STATUS_CHOICES

    route_group = models.ForeignKey(
        RouteCorridorGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="structure_entries",
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

    boq_status = models.CharField(
        max_length=20, choices=INSPECTION_STATUS_CHOICES, blank=True, default=""
    )
    boq_remark = models.TextField(blank=True, default="")
    lidar_status = models.CharField(
        max_length=20, choices=INSPECTION_STATUS_CHOICES, blank=True, default=""
    )
    lidar_remark = models.TextField(blank=True, default="")
    sar_status = models.CharField(
        max_length=20, choices=INSPECTION_STATUS_CHOICES, blank=True, default=""
    )
    sar_remark = models.TextField(blank=True, default="")

    has_boq = models.BooleanField(default=False)
    has_lidar = models.BooleanField(default=False)
    has_sar = models.BooleanField(default=False)

    las_file_submitted = models.BooleanField(default=False)
    reports_available_on_bms_for_las = models.BooleanField(default=False)
    sar_files_submitted = models.BooleanField(default=False)
    reports_available_on_bms_for_sar = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Structure entry (unified)"
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["date_of_entry"]),
            models.Index(fields=["route_group"]),
            models.Index(fields=["has_boq"]),
            models.Index(fields=["has_lidar"]),
            models.Index(fields=["has_sar"]),
        ]

    def __str__(self):
        ch = self.chainage or "-"
        dt = self.date_of_entry or "-"
        return f"{ch} | {dt}"


class InfraServiceType(models.Model):
    """
    Configurable infra service codes (dropdown source). Extend by adding rows in admin.
    Codes ``boq``, ``lidar``, ``sar`` mirror legacy columns via sync helpers.
    """

    code = models.SlugField(max_length=40, unique=True, db_index=True)
    label = models.CharField(max_length=160)
    sort_order = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "code"]
        verbose_name = "Infrastructure service type"
        verbose_name_plural = "Infrastructure service types"

    def __str__(self):
        return f"{self.label} ({self.code})"


class StructureEntryServiceState(models.Model):
    """
    Status + remark per service type per structure row. Supports services beyond BOQ/LiDAR/SAR.
    Legacy columns remain the compatibility surface for the three built-in modules.
    """

    structure_entry = models.ForeignKey(
        StructureEntry,
        on_delete=models.CASCADE,
        related_name="service_states",
    )
    service_type = models.ForeignKey(
        InfraServiceType,
        on_delete=models.CASCADE,
        related_name="structure_entry_states",
    )
    inspection_status = models.CharField(
        max_length=20,
        choices=StructureEntry.INSPECTION_STATUS_CHOICES,
        blank=True,
        default="",
    )
    remark = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("structure_entry", "service_type"),
                name="infra_entry_service_unique",
            )
        ]
        ordering = ["structure_entry_id", "service_type__sort_order", "service_type_id"]
        verbose_name = "Structure entry service state"
        verbose_name_plural = "Structure entry service states"

    def __str__(self):
        return f"{self.structure_entry_id}: {self.service_type.code}"


class InfraProjectForm(models.Model):
    """
    Header record for project-level numeric capture (separate from BOQ/LiDAR/SAR tables).
    Kept isolated to avoid impacting existing infra_forms functionality.
    """

    project = models.ForeignKey(
        ProjectCatalog,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="infra_project_forms",
    )
    projectname = models.CharField(max_length=160, blank=True, default="")
    creator = models.CharField(max_length=120, blank=True, default="")
    date = models.DateField(null=True, blank=True)

    MJB = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    MNB = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    VUP = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    PUP = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    BOX_Slab_Culvert = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    ROB = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    FO = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        indexes = [
            models.Index(fields=["projectname"]),
            models.Index(fields=["date"]),
            models.Index(fields=["project"]),
        ]

    def __str__(self):
        name = self.projectname or (self.project.name if self.project_id else "")
        dt = self.date or "-"
        return f"{name or '-'} | {dt}"


class InfraProjectFormEntry(models.Model):
    """Child rows for `InfraProjectForm` (Entry[])."""

    form = models.ForeignKey(InfraProjectForm, on_delete=models.CASCADE, related_name="entries")
    date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text="Optional status value sent by frontend (static dropdown).",
    )

    MJB = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    MNB = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    VUP = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    PUP = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    BOX_Slab_Culvert = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    ROB = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    FO = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["form"]),
            models.Index(fields=["date"]),
        ]
