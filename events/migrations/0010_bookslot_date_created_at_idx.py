# Generated manually for query optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0009_holiday'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='bookslot',
            index=models.Index(fields=['-date', '-created_at'], name='bookslot_date_created_idx'),
        ),
    ]
