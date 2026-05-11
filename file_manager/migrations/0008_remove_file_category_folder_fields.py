from django.db import migrations


def strip_legacy_hierarchy_rows(apps, schema_editor):
    File = apps.get_model("file_manager", "File")
    File.objects.filter(is_folder=False).update(folder=None)
    File.objects.filter(is_folder=True).delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("file_manager", "0007_fileversion_revision_blob_fields"),
    ]

    operations = [
        migrations.RunPython(strip_legacy_hierarchy_rows, noop_reverse),
        migrations.RemoveField(model_name="file", name="category"),
        migrations.RemoveField(model_name="file", name="folder"),
        migrations.RemoveField(model_name="file", name="is_folder"),
        migrations.DeleteModel(name="FileCategory"),
    ]
