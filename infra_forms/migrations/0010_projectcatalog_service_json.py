# Generated manually: convert ProjectCatalog.service from varchar -> jsonb without data loss.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("infra_forms", "0009_infraprojectformentry_status"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE infra_forms_projectcatalog
                      RENAME COLUMN service TO service_old;

                    ALTER TABLE infra_forms_projectcatalog
                      ADD COLUMN service jsonb NOT NULL DEFAULT '[]'::jsonb;

                    UPDATE infra_forms_projectcatalog
                    SET service = CASE
                      WHEN service_old IS NULL OR btrim(service_old::text) = '' THEN '[]'::jsonb
                      ELSE json_build_array(service_old)::jsonb
                    END;

                    ALTER TABLE infra_forms_projectcatalog
                      DROP COLUMN service_old;
                    """,
                    reverse_sql="""
                    ALTER TABLE infra_forms_projectcatalog
                      ADD COLUMN service_old varchar(160) NOT NULL DEFAULT '';

                    UPDATE infra_forms_projectcatalog
                    SET service_old = CASE
                      WHEN service IS NULL OR service = '[]'::jsonb THEN ''
                      WHEN jsonb_typeof(service) = 'array' AND jsonb_array_length(service) > 0
                        THEN service->>0
                      ELSE ''
                    END;

                    ALTER TABLE infra_forms_projectcatalog
                      DROP COLUMN service;

                    ALTER TABLE infra_forms_projectcatalog
                      RENAME COLUMN service_old TO service;
                    """,
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="projectcatalog",
                    name="service",
                    field=models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Optional list of service values from frontend dropdown(s).",
                    ),
                ),
            ],
        ),
    ]
