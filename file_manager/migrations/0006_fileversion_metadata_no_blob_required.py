from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("file_manager", "0005_file_storage_provider_default_local"),
    ]

    operations = [
        migrations.AddField(
            model_name="fileversion",
            name="snapshot_size",
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="fileversion",
            name="snapshot_storage_path",
            field=models.CharField(blank=True, default="", max_length=1024),
        ),
        migrations.AddField(
            model_name="fileversion",
            name="snapshot_storage_provider",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="fileversion",
            name="snapshot_title",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="fileversion",
            name="version_file",
            field=models.FileField(blank=True, null=True, upload_to="file_versions/"),
        ),
    ]
