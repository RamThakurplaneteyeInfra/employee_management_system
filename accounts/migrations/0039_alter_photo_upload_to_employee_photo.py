# Photo_link upload_to: profile_images/ -> Employee_Photo/ (S3 prefix)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0038_alter_profilefunction_profile"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="Photo_link",
            field=models.ImageField(
                blank=True,
                height_field=None,
                max_length=None,
                null=True,
                upload_to="Employee_Photo/",
                verbose_name="image_link",
                width_field=None,
            ),
        ),
        migrations.AlterField(
            model_name="management_profile",
            name="Photo_link",
            field=models.ImageField(
                blank=True,
                height_field=None,
                max_length=None,
                null=True,
                upload_to="Employee_Photo/",
                verbose_name="image_link",
                width_field=None,
            ),
        ),
    ]
