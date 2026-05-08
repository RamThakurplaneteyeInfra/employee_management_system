"""Copy legacy per-module rows into the unified StructureEntry table.

Safety guarantees:
- Old tables (BoqStructureEntry / LidarStructureEntry / SarStructureEntry) are NOT touched.
  All legacy rows remain in their original tables as a permanent backup.
- Each old row produces exactly one new row in StructureEntry (no merging),
  so nothing can be accidentally combined or lost.
- Django's migration framework guarantees this runs exactly once per database,
  so explicit idempotency is not required.
- Remark text is copied EXACTLY as it was; no markers are injected, so the
  data the user sees in the UI is unchanged.
- The reverse migration is intentionally a no-op (raises) to prevent
  accidental destruction of the unified table after rollback. To revert,
  use `migrate infra_forms 0010` and then drop the unified table manually
  if desired.
"""

from django.db import migrations


def _copy_module_rows(apps, module_key: str, legacy_model_name: str) -> int:
    Legacy = apps.get_model("infra_forms", legacy_model_name)
    Structure = apps.get_model("infra_forms", "StructureEntry")

    status_field = f"{module_key}_status"
    remark_field = f"{module_key}_remark"
    has_field = f"has_{module_key}"

    created = 0
    for old in Legacy.objects.all().iterator():
        Structure.objects.create(
            route_group=old.route_group,
            project_name=old.project_name,
            team_lead_name=old.team_lead_name,
            branch=old.branch or "INFRA_CORE",
            date_of_entry=old.date_of_entry,
            route_corridor=old.route_corridor,
            sr_no=old.sr_no,
            chainage=old.chainage,
            structure_type=old.structure_type,
            length_of_structure=old.length_of_structure,
            span_arrangement=old.span_arrangement,
            equipment_notes=old.equipment_notes,
            las_file_submitted=old.las_file_submitted,
            reports_available_on_bms_for_las=old.reports_available_on_bms_for_las,
            sar_files_submitted=old.sar_files_submitted,
            reports_available_on_bms_for_sar=old.reports_available_on_bms_for_sar,
            **{
                status_field: old.inspection_status or "",
                remark_field: old.remark or "",
                has_field: True,
            },
        )
        created += 1
    return created


def copy_forward(apps, schema_editor):
    _copy_module_rows(apps, "boq", "BoqStructureEntry")
    _copy_module_rows(apps, "lidar", "LidarStructureEntry")
    _copy_module_rows(apps, "sar", "SarStructureEntry")


def copy_reverse(apps, schema_editor):
    """No-op: legacy tables still hold all data; do not auto-purge unified rows."""
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("infra_forms", "0011_create_structureentry"),
    ]

    operations = [
        migrations.RunPython(copy_forward, copy_reverse),
    ]
