from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("file_manager", "0004_file_yandex_storage_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="file",
            name="storage_provider",
            field=models.CharField(
                choices=[("local", "Local"), ("yandex_disk", "Yandex Disk")],
                default="local",
                max_length=20,
            ),
        ),
    ]
