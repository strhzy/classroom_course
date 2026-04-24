from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("classroom_core", "0005_course_start_end_date_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseLesson",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lesson_date", models.DateField()),
                ("lesson_number", models.PositiveSmallIntegerField(default=1)),
                ("topic", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lessons", to="classroom_core.course")),
            ],
            options={
                "ordering": ["lesson_date", "lesson_number", "id"],
                "unique_together": {("course", "lesson_date", "lesson_number")},
            },
        ),
        migrations.CreateModel(
            name="LessonGrade",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("mark", models.CharField(blank=True, max_length=8)),
                ("feedback", models.TextField(blank=True)),
                ("graded_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("graded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="graded_lesson_grades", to=settings.AUTH_USER_MODEL)),
                ("lesson", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="grades", to="classroom_core.courselesson")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lesson_grades", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "unique_together": {("lesson", "student")},
            },
        ),
    ]
