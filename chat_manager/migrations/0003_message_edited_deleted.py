from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat_manager", "0002_message_file_attachment_alter_message_content"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="edited_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="message",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
    ]
