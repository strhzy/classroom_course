from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("classroom_core", "0002_alter_assignment_course"),
    ]

    operations = [
        migrations.AddField(
            model_name="coursematerial",
            name="status",
            field=models.CharField(
                choices=[("draft", "Черновик"), ("published", "Опубликовано")],
                default="published",
                max_length=20,
            ),
        ),
    ]
