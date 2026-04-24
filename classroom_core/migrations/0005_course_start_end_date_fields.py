from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("classroom_core", "0004_course_schedule_profile_access_gradebook_columns"),
    ]

    operations = [
        migrations.AlterField(
            model_name="course",
            name="start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="course",
            name="end_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
