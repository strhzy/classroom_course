                                               

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('classroom_core', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assignment',
            name='course',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='classroom_core.course'),
        ),
    ]
