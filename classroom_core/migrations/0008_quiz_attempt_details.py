from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("classroom_core", "0007_assignment_quiz_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignmentquizattempt",
            name="answers_payload",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="assignmentquizattempt",
            name="correct_answers",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="assignmentquizattempt",
            name="total_questions",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
