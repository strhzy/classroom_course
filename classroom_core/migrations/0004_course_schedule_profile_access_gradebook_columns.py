from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("classroom_core", "0003_coursematerial_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="class_days",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="course",
            name="class_time",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="access_class",
            field=models.CharField(
                choices=[("main", "Основное"), ("important", "Важное"), ("secondary", "Не важное")],
                default="main",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="GradebookColumn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("column_type", models.CharField(choices=[("lecture", "Лекция"), ("attendance", "Посещаемость"), ("exam", "Экзамен"), ("custom", "Кастом")], default="custom", max_length=20)),
                ("max_points", models.IntegerField(default=100)),
                ("order", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="gradebook_columns", to="classroom_core.course")),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.CreateModel(
            name="GradebookRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.IntegerField(blank=True, null=True)),
                ("status", models.CharField(default="graded", max_length=20)),
                ("feedback", models.TextField(blank=True)),
                ("graded_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("column", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="records", to="classroom_core.gradebookcolumn")),
                ("graded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="graded_gradebook_records", to=settings.AUTH_USER_MODEL)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="gradebook_records", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name="gradebookrecord",
            unique_together={("column", "student")},
        ),
    ]
