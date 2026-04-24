                                               

import chat_manager.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat_manager', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='file_attachment',
            field=models.FileField(blank=True, null=True, upload_to=chat_manager.models.message_file_upload_path, verbose_name='Файл'),
        ),
        migrations.AlterField(
            model_name='message',
            name='content',
            field=models.TextField(blank=True),
        ),
    ]
