from django.db import migrations, models
import file_manager.models


class Migration(migrations.Migration):

    dependencies = [
        ("file_manager", "0003_importance_favorites_workspaces"),
    ]

    operations = [
        migrations.AlterField(
            model_name="file",
            name="file",
            field=models.FileField(blank=True, null=True, upload_to=file_manager.models.file_upload_path),
        ),
        migrations.AddField(
            model_name="file",
            name="storage_provider",
            field=models.CharField(
                choices=[("local", "Local"), ("yandex_disk", "Yandex Disk")],
                default="yandex_disk",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="file",
            name="yandex_path",
            field=models.CharField(blank=True, default="", max_length=1024),
        ),
    ]
