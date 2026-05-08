from rest_framework import serializers

from .models import (
    InfraProjectForm,
    InfraProjectFormEntry,
    InfraServiceType,
    ProjectCatalog,
    RouteCorridorGroup,
    StructureEntry,
)
from .service_state_sync import (
    build_services_representation,
    mirror_legacy_columns_to_service_states,
    mirror_service_states_to_legacy_columns,
    upsert_service_states_merge,
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
    """
    All three module serializers (BOQ/LiDAR/SAR) share this base.

    The unified `StructureEntry` table stores per-module status/remark in
    `boq_status`/`boq_remark`, `lidar_status`/`lidar_remark`,
    `sar_status`/`sar_remark`. Each subclass uses `source=` mapping so the
    JSON shape the frontend sees stays IDENTICAL to the legacy API
    (`inspection_status` and `remark` keys).
    """

    route_group = serializers.PrimaryKeyRelatedField(read_only=True)
    inspection_status = serializers.ChoiceField(
        choices=StructureEntry.INSPECTION_STATUS_CHOICES,
        required=False,
        allow_blank=True,
        default="",
    )
    remark = serializers.CharField(required=False, allow_blank=True, default="")
    services = serializers.SerializerMethodField(read_only=True)

    entry_module = None  # "boq" | "lidar" | "sar"

    def get_services(self, obj):
        return build_services_representation(obj)

    class Meta:
        model = StructureEntry
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
            "services",
            "las_file_submitted",
            "reports_available_on_bms_for_las",
            "sar_files_submitted",
            "reports_available_on_bms_for_sar",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "route_group", "services", "created_at", "updated_at"]

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

    def _module_fields(self):
        """Return (status_field, remark_field, has_field) for this serializer's module."""
        m = self.entry_module
        return f"{m}_status", f"{m}_remark", f"has_{m}"

    def _apply_module_mapping(self, validated_data):
        """Move incoming `inspection_status`/`remark` into module-specific columns."""
        status_field, remark_field, has_field = self._module_fields()
        if "inspection_status" in validated_data:
            validated_data[status_field] = validated_data.pop("inspection_status") or ""
        if "remark" in validated_data:
            validated_data[remark_field] = validated_data.pop("remark") or ""
        validated_data[has_field] = True

    def to_representation(self, instance):
        """Render JSON with `inspection_status`/`remark` taken from the module's columns."""
        data = super().to_representation(instance)
        status_field, remark_field, _ = self._module_fields()
        data["inspection_status"] = getattr(instance, status_field, "") or ""
        data["remark"] = getattr(instance, remark_field, "") or ""
        return data

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
        self._apply_module_mapping(validated_data)
        instance = super().create(validated_data)
        mirror_legacy_columns_to_service_states(instance)
        return instance

    def update(self, instance, validated_data):
        module = self.entry_module
        if "route_corridor" in validated_data:
            route_text = validated_data.get("route_corridor", instance.route_corridor)
            self._sync_route_corridor_group(module, route_text, validated_data)
        self._apply_module_mapping(validated_data)
        instance = super().update(instance, validated_data)
        mirror_legacy_columns_to_service_states(instance)
        return instance


class BoqStructureEntrySerializer(BaseStructureEntrySerializer):
    entry_module = "boq"


class LidarStructureEntrySerializer(BaseStructureEntrySerializer):
    entry_module = "lidar"


class SarStructureEntrySerializer(BaseStructureEntrySerializer):
    entry_module = "sar"


_UNIFIED_MODULE_ORDER = ("boq", "lidar", "sar")


class UnifiedStructureEntrySerializer(serializers.ModelSerializer):
    """
    One payload for all modules: `inspection_status` and `remark` are length-3
    lists in order [BOQ, LiDAR, SAR]. Does not alter legacy per-module serializers.

    Optional `services` (write): list of ``{code, inspection_status?, remark?}`` objects;
    merges by service code into `StructureEntryServiceState` (see also read-only ``services``
    with ``code`` + ``label`` for each row). Do not combine with the legacy triple list fields.
    """

    inspection_status = serializers.ListField(
        child=serializers.ChoiceField(
            choices=StructureEntry.INSPECTION_STATUS_CHOICES,
            allow_blank=True,
        ),
        required=False,
        allow_empty=True,
        write_only=True,
    )
    remark = serializers.ListField(
        child=serializers.CharField(allow_blank=True, required=False, default=""),
        required=False,
        allow_empty=True,
        write_only=True,
    )

    route_group = serializers.PrimaryKeyRelatedField(read_only=True)
    services = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StructureEntry
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
            "las_file_submitted",
            "reports_available_on_bms_for_las",
            "sar_files_submitted",
            "reports_available_on_bms_for_sar",
            "inspection_status",
            "remark",
            "services",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "route_group", "services", "created_at", "updated_at"]

    def get_services(self, obj):
        return build_services_representation(obj)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        shared = (
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
            "las_file_submitted",
            "reports_available_on_bms_for_las",
            "sar_files_submitted",
            "reports_available_on_bms_for_sar",
        )
        for name in shared:
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

    def _normalize_triple(self, value, *, for_status: bool) -> list:
        if value is None:
            return ["", "", ""]
        if not isinstance(value, (list, tuple)):
            raise serializers.ValidationError("Must be a list.")
        if len(value) > 3:
            raise serializers.ValidationError(
                "Must contain at most 3 elements [BOQ, LiDAR, SAR]."
            )
        out: list[str] = []
        allowed = {c[0] for c in StructureEntry.INSPECTION_STATUS_CHOICES}
        for i in range(3):
            if i < len(value):
                raw = value[i]
                s = "" if raw is None else str(raw).strip()
            else:
                s = ""
            if for_status and s and s not in allowed:
                raise serializers.ValidationError(f"Invalid status: {raw!r}.")
            out.append(s)
        return out

    def validate_inspection_status(self, value):
        return self._normalize_triple(value, for_status=True)

    def validate_remark(self, value):
        return self._normalize_triple(value, for_status=False)

    def _normalize_services_payload(self, raw) -> list[dict[str, str]]:
        if not isinstance(raw, list):
            raise serializers.ValidationError({"services": "Must be a list of objects."})
        allowed = {c[0] for c in StructureEntry.INSPECTION_STATUS_CHOICES}
        by_code: dict[str, dict[str, str]] = {}
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                raise serializers.ValidationError(
                    {"services": f"Item {i} must be an object with at least a code."}
                )
            code = item.get("code")
            code = "" if code is None else str(code).strip().lower()
            if not code:
                raise serializers.ValidationError(
                    {"services": f"Item {i} must include a non-empty code."}
                )
            st = item.get("inspection_status")
            st = "" if st is None else str(st).strip()
            if st and st not in allowed:
                raise serializers.ValidationError(
                    {"services": f"Invalid inspection_status for {code!r}."}
                )
            rm = item.get("remark")
            rm = "" if rm is None else str(rm)
            by_code[code] = {"code": code, "inspection_status": st, "remark": rm}
        return list(by_code.values())

    def validate(self, attrs):
        initial = getattr(self, "initial_data", None) or {}
        if initial.get("services") is not None:
            payload = self._normalize_services_payload(initial["services"])
            if "inspection_status" in initial or "remark" in initial:
                raise serializers.ValidationError(
                    {
                        "services": (
                            "Do not combine `services` with `inspection_status` / `remark` list fields."
                        ),
                    }
                )
            attrs["_services_write"] = payload
            if self.instance is None:
                has_content = False
                for row in payload:
                    if (row["inspection_status"] or "").strip() or (
                        row["remark"] or ""
                    ).strip():
                        has_content = True
                        break
                if not has_content:
                    raise serializers.ValidationError(
                        {
                            "services": (
                                "Provide at least one non-empty inspection_status "
                                "or remark on create."
                            )
                        }
                    )
            return attrs

        if self.instance is None:
            st = attrs.get("inspection_status")
            rm = attrs.get("remark")
            if st is None:
                st = ["", "", ""]
            if rm is None:
                rm = ["", "", ""]
            if not any(st[i] or rm[i] for i in range(3)):
                raise serializers.ValidationError(
                    "Provide at least one non-empty status or remark across BOQ, LiDAR, or SAR."
                )
        return attrs

    def _sync_route_corridor_group(self, route_text, data: dict) -> None:
        """Use BOQ module key for RouteCorridorGroup — same row has one FK."""
        route = (route_text or "").strip()
        if not route:
            data["route_group"] = None
            data["route_corridor"] = ""
            return
        key = route.casefold()
        group, _ = RouteCorridorGroup.objects.get_or_create(
            module="boq",
            route_key=key,
            defaults={"route_label": route},
        )
        data["route_group"] = group
        data["route_corridor"] = group.route_label

    def _apply_triples_to_model_attrs(self, data: dict, statuses: list, remarks: list) -> None:
        for i, m in enumerate(_UNIFIED_MODULE_ORDER):
            st = statuses[i] if i < len(statuses) else ""
            rm = remarks[i] if i < len(remarks) else ""
            st = st or ""
            rm = rm or ""
            data[f"{m}_status"] = st
            data[f"{m}_remark"] = rm
            data[f"has_{m}"] = bool(st) or bool(rm.strip())

    def create(self, validated_data):
        services_write = validated_data.pop("_services_write", None)
        if services_write is not None:
            validated_data.pop("inspection_status", None)
            validated_data.pop("remark", None)
            for m in _UNIFIED_MODULE_ORDER:
                validated_data[f"{m}_status"] = ""
                validated_data[f"{m}_remark"] = ""
                validated_data[f"has_{m}"] = False
            route_text = validated_data.get("route_corridor", "")
            self._sync_route_corridor_group(route_text, validated_data)
            instance = StructureEntry.objects.create(**validated_data)
            try:
                upsert_service_states_merge(instance, services_write)
            except ValueError as exc:
                instance.delete()
                raise serializers.ValidationError({"services": [str(exc)]}) from exc
            mirror_service_states_to_legacy_columns(instance)
            return instance

        statuses = validated_data.pop(
            "inspection_status", self._normalize_triple(None, for_status=True)
        )
        remarks = validated_data.pop("remark", self._normalize_triple(None, for_status=False))
        route_text = validated_data.get("route_corridor", "")
        self._sync_route_corridor_group(route_text, validated_data)
        self._apply_triples_to_model_attrs(validated_data, statuses, remarks)
        instance = StructureEntry.objects.create(**validated_data)
        mirror_legacy_columns_to_service_states(instance)
        return instance

    def update(self, instance, validated_data):
        services_write = validated_data.pop("_services_write", None)
        has_st = "inspection_status" in validated_data
        has_rm = "remark" in validated_data
        if has_st or has_rm:
            statuses = validated_data.pop("inspection_status", None) if has_st else None
            remarks = validated_data.pop("remark", None) if has_rm else None
            if statuses is None:
                statuses = [
                    getattr(instance, f"{m}_status") or "" for m in _UNIFIED_MODULE_ORDER
                ]
            if remarks is None:
                remarks = [
                    getattr(instance, f"{m}_remark") or "" for m in _UNIFIED_MODULE_ORDER
                ]
            statuses = self._normalize_triple(statuses, for_status=True)
            remarks = self._normalize_triple(remarks, for_status=False)
            self._apply_triples_to_model_attrs(validated_data, statuses, remarks)

        if "route_corridor" in validated_data:
            route_text = validated_data.get("route_corridor", instance.route_corridor)
            self._sync_route_corridor_group(route_text, validated_data)
        instance = super().update(instance, validated_data)
        if services_write is not None:
            try:
                upsert_service_states_merge(instance, services_write)
            except ValueError as exc:
                raise serializers.ValidationError({"services": [str(exc)]}) from exc
            mirror_service_states_to_legacy_columns(instance)
        else:
            mirror_legacy_columns_to_service_states(instance)
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["inspection_status"] = [
            getattr(instance, f"{m}_status") or "" for m in _UNIFIED_MODULE_ORDER
        ]
        data["remark"] = [
            getattr(instance, f"{m}_remark") or "" for m in _UNIFIED_MODULE_ORDER
        ]
        return data


class InfraServiceTypeSerializer(serializers.ModelSerializer):
    """Infra structure service types (dropdown + CRUD API)."""

    class Meta:
        model = InfraServiceType
        fields = ["id", "code", "label", "sort_order", "active"]
        read_only_fields = ["id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("code", "label", "sort_order", "active"):
            fld = self.fields.get(name)
            if not fld:
                continue
            if name == "sort_order":
                fld.required = False
            elif name == "active":
                fld.required = False

    def validate_code(self, value):
        normalized = "" if value is None else str(value).strip().lower()
        if not normalized:
            raise serializers.ValidationError("This field may not be blank.")
        return normalized

    def validate_label(self, value):
        if value is None or not str(value).strip():
            raise serializers.ValidationError("This field may not be blank.")
        return str(value).strip()


class ProjectCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectCatalog
        fields = ["id", "name", "service", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_service(self, value):
        """
        Accept:
        - list[str] (preferred)
        - single str (backward compatible with older clients)
        """
        if value in (None, "", []):
            return []
        if isinstance(value, str):
            v = value.strip()
            return [v] if v else []
        if isinstance(value, (list, tuple)):
            out: list[str] = []
            for x in value:
                if x is None:
                    continue
                s = str(x).strip()
                if s:
                    out.append(s)
            return out
        raise serializers.ValidationError("service must be a list of strings or a single string.")


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
        fields = ["id", "date", "status", *_INFRA_NUMERIC_FIELDS, "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("date", "status", *_INFRA_NUMERIC_FIELDS):
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
