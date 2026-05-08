from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("file_manager", "0006_fileversion_metadata_no_blob_required"),
    ]

    operations = [
        migrations.AddField(
            model_name="fileversion",
            name="blob_sha256",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="fileversion",
            name="blob_size",
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="fileversion",
            name="blob_storage_path",
            field=models.CharField(blank=True, default="", max_length=1024),
        ),
        migrations.AddField(
            model_name="fileversion",
            name="blob_storage_provider",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="fileversion",
            name="extracted_text_snapshot",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="fileversion",
            name="has_blob",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="fileversion",
            name="structured_schema_version",
            field=models.CharField(blank=True, default="v1", max_length=32),
        ),
        migrations.AddField(
            model_name="fileversion",
            name="structured_snapshot",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
