# Generated manually for query optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['receipient', '-created_at'], name='notif_rec_created_idx'),
        ),
    ]
