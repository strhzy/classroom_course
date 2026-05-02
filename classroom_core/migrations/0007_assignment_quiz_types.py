from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("classroom_core", "0006_course_lesson_and_marks"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="assignment",
            name="assignment_type",
            field=models.CharField(
                choices=[("file_upload", "Прикрепление файла"), ("quiz", "Тест")],
                default="file_upload",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="assignment",
            name="quiz_mode",
            field=models.CharField(
                choices=[("single", "Один правильный ответ"), ("multiple", "Несколько правильных ответов")],
                default="single",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="AssignmentQuizAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_correct", models.BooleanField(default=False)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("assignment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quiz_attempts", to="classroom_core.assignment")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quiz_attempts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-submitted_at"]},
        ),
        migrations.CreateModel(
            name="AssignmentQuizQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question_text", models.TextField()),
                ("order", models.PositiveIntegerField(default=0)),
                ("assignment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quiz_questions", to="classroom_core.assignment")),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.CreateModel(
            name="AssignmentQuizOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("option_text", models.CharField(max_length=500)),
                ("is_correct", models.BooleanField(default=False)),
                ("order", models.PositiveIntegerField(default=0)),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="options", to="classroom_core.assignmentquizquestion")),
            ],
            options={"ordering": ["order", "id"]},
        ),
    ]
