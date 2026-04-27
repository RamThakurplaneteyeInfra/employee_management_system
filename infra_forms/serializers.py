from rest_framework import serializers

from .models import (
    BoqStructureEntry,
    InfraProjectForm,
    InfraProjectFormEntry,
    LidarStructureEntry,
    ProjectCatalog,
    RouteCorridorGroup,
    SarStructureEntry,
)

_WRITABLE_OPTIONAL_FIELDS = (
    "project_name",
    "team_lead_name",
    "branch",
    "date_of_entry",
    "route_corridor",
    "sr_no",
    "chainage",
    "structure_type",
    "length_of_structure",
    "span_arrangement",
    "equipment_notes",
    "inspection_status",
    "remark",
    "las_file_submitted",
    "reports_available_on_bms_for_las",
    "sar_files_submitted",
    "reports_available_on_bms_for_sar",
)


class BaseStructureEntrySerializer(serializers.ModelSerializer):
    """Shared create/update/route-group sync; `Meta.model` and `entry_module` set on subclass."""

    route_group = serializers.PrimaryKeyRelatedField(read_only=True)
    entry_module = None  # "boq" | "lidar" | "sar"

    class Meta:
        fields = [
            "id",
            "route_group",
            "project_name",
            "team_lead_name",
            "branch",
            "date_of_entry",
            "route_corridor",
            "sr_no",
            "chainage",
            "structure_type",
            "length_of_structure",
            "span_arrangement",
            "equipment_notes",
            "inspection_status",
            "remark",
            "las_file_submitted",
            "reports_available_on_bms_for_las",
            "sar_files_submitted",
            "reports_available_on_bms_for_sar",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "route_group", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ModelSerializer can still infer required=True for some setups; bulk rows often omit keys.
        for name in _WRITABLE_OPTIONAL_FIELDS:
            field = self.fields.get(name)
            if not field:
                continue
            field.required = False
            if isinstance(field, serializers.BooleanField):
                continue
            if name == "date_of_entry" and getattr(field, "allow_null", None) is not None:
                field.allow_null = True
            if getattr(field, "allow_blank", None) is not None:
                field.allow_blank = True

    def _sync_route_corridor_group(self, module, route_text, validated_data):
        route = (route_text or "").strip()
        if not route:
            validated_data["route_group"] = None
            validated_data["route_corridor"] = ""
            return
        key = route.casefold()
        group, _ = RouteCorridorGroup.objects.get_or_create(
            module=module,
            route_key=key,
            defaults={"route_label": route},
        )
        validated_data["route_group"] = group
        validated_data["route_corridor"] = group.route_label

    def create(self, validated_data):
        module = self.entry_module
        route_text = validated_data.get("route_corridor", "")
        self._sync_route_corridor_group(module, route_text, validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        module = self.entry_module
        if "route_corridor" in validated_data:
            route_text = validated_data.get("route_corridor", instance.route_corridor)
            self._sync_route_corridor_group(module, route_text, validated_data)
        return super().update(instance, validated_data)


class BoqStructureEntrySerializer(BaseStructureEntrySerializer):
    entry_module = "boq"

    class Meta(BaseStructureEntrySerializer.Meta):
        model = BoqStructureEntry


class LidarStructureEntrySerializer(BaseStructureEntrySerializer):
    entry_module = "lidar"

    class Meta(BaseStructureEntrySerializer.Meta):
        model = LidarStructureEntry


class SarStructureEntrySerializer(BaseStructureEntrySerializer):
    entry_module = "sar"

    class Meta(BaseStructureEntrySerializer.Meta):
        model = SarStructureEntry


class ProjectCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectCatalog
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


_INFRA_NUMERIC_FIELDS = (
    "MJB",
    "MNB",
    "VUP",
    "PUP",
    "BOX_Slab_Culvert",
    "ROB",
    "FO",
)


class InfraProjectFormEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = InfraProjectFormEntry
        fields = ["id", "date", *_INFRA_NUMERIC_FIELDS, "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("date", *_INFRA_NUMERIC_FIELDS):
            f = self.fields.get(name)
            if not f:
                continue
            f.required = False
            if getattr(f, "allow_null", None) is not None:
                f.allow_null = True


class InfraProjectFormSerializer(serializers.ModelSerializer):
    entries = InfraProjectFormEntrySerializer(many=True, required=False)

    class Meta:
        model = InfraProjectForm
        fields = [
            "id",
            "project",
            "projectname",
            "creator",
            "date",
            *_INFRA_NUMERIC_FIELDS,
            "entries",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("project", "projectname", "creator", "date", *_INFRA_NUMERIC_FIELDS):
            f = self.fields.get(name)
            if not f:
                continue
            f.required = False
            if getattr(f, "allow_null", None) is not None:
                f.allow_null = True
            if getattr(f, "allow_blank", None) is not None:
                f.allow_blank = True

    def create(self, validated_data):
        entries_data = validated_data.pop("entries", None) or []
        form = InfraProjectForm.objects.create(**validated_data)
        if entries_data:
            InfraProjectFormEntry.objects.bulk_create(
                [InfraProjectFormEntry(form=form, **row) for row in entries_data]
            )
        return form

    def update(self, instance, validated_data):
        """
        Safe update rules (to avoid accidental data loss):
        - If request omits `entries`, existing entries are untouched.
        - If request includes `entries`, entries are replaced atomically.
        """
        entries_present = "entries" in validated_data
        entries_data = validated_data.pop("entries", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if entries_present:
            instance.entries.all().delete()
            if entries_data:
                InfraProjectFormEntry.objects.bulk_create(
                    [InfraProjectFormEntry(form=instance, **row) for row in entries_data]
                )
        return instance
