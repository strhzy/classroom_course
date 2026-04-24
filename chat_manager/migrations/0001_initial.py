                                               

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('classroom_core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatRoom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('room_type', models.CharField(choices=[('course', 'Курс'), ('private', 'Личный'), ('group', 'Групповой')], default='private', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('course', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='chat_rooms', to='classroom_core.course')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_rooms', to=settings.AUTH_USER_MODEL)),
                ('participants', models.ManyToManyField(related_name='chat_rooms', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Комната чата',
                'verbose_name_plural': 'Комнаты чата',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('is_read', models.BooleanField(default=False)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='chat_manager.chatroom')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Сообщение',
                'verbose_name_plural': 'Сообщения',
                'ordering': ['timestamp'],
                'indexes': [models.Index(fields=['room', '-timestamp'], name='chat_manage_room_id_91d546_idx'), models.Index(fields=['user', '-timestamp'], name='chat_manage_user_id_115cef_idx')],
            },
        ),
    ]
