# Migration: unique_together (product, date) and default for Conversion_percent

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('QuaterlyReports', '0016_alter_salesstatistics_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='salesstatistics',
            name='Conversion_percent',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
        migrations.AlterUniqueTogether(
            name='salesstatistics',
            unique_together={('product', 'date')},
        ),
    ]
