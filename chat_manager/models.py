from django.db import models
from django.contrib.auth.models import User
from classroom_core.models import Course
import os

def message_file_upload_path(instance, filename):
    """Путь для загрузки файлов в сообщениях чата"""
    from django.utils import timezone
    ext = filename.split('.')[-1].lower()
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    new_filename = f"chat{instance.room.id}_msg{timestamp}.{ext}"
    return os.path.join('chat_files', str(instance.room.id), new_filename)

class ChatRoom(models.Model):
    """Модель комнаты чата"""
    ROOM_TYPE_CHOICES = [
        ('course', 'Курс'),
        ('private', 'Личный'),
        ('group', 'Групповой'),
    ]
    
    name = models.CharField(max_length=255)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES, default='private')
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='chat_rooms'
    )
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Комната чата'
        verbose_name_plural = 'Комнаты чата'
    
    def __str__(self):
        return self.name
    
    def get_last_message(self):
        """Получить последнее сообщение"""
        return self.messages.order_by('-timestamp').first()
    
    @classmethod
    def get_or_create_private_chat(cls, user1, user2):
        """Получить или создать личный чат между двумя пользователями"""
                                
        rooms = cls.objects.filter(
            room_type='private',
            is_active=True,
            participants=user1
        ).filter(participants=user2)
        
        if rooms.exists():
            return rooms.first()
        
                           
        room_name = f"Чат с {user2.username}"
        room = cls.objects.create(
            name=room_name,
            room_type='private',
            created_by=user1
        )
        room.participants.set([user1, user2])
        return room

class Message(models.Model):
    """Модель сообщения"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField(blank=True)
    file_attachment = models.FileField(
        upload_to=message_file_upload_path,
        null=True,
        blank=True,
        verbose_name='Файл'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        indexes = [
            models.Index(fields=['room', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]
    
    def __str__(self):
        if self.file_attachment:
            return f"{self.user.username}: 📎 {self.file_attachment.name.split('/')[-1]}"
        return f"{self.user.username}: {self.content[:50]}"
    
    def mark_as_read(self):
        """Отметить сообщение как прочитанное"""
        self.is_read = True
        self.save(update_fields=['is_read'])
    
    def is_image(self):
        """Проверить, является ли файл изображением"""
        if not self.file_attachment:
            return False
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
        ext = self.file_attachment.name.split('.')[-1].lower()
        return ext in image_extensions
    
    def get_file_extension(self):
        """Получить расширение файла"""
        if not self.file_attachment:
            return ''
        return self.file_attachment.name.split('.')[-1].upper()
    
    def get_file_size_display(self):
        """Отображение размера файла"""
        if not self.file_attachment:
            return ''
        try:
            size = self.file_attachment.size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        except Exception:
            return ''

    def get_icon(self):
        if not self.file_attachment:
            return '📎'
        ext = self.file_attachment.name.split('.')[-1].lower()
        icons = {
            'pdf': '📄', 'txt': '📝', 'doc': '📑', 'docx': '📑',
            'xls': '📊', 'xlsx': '📊', 'ppt': '📽️', 'pptx': '📽️',
            'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'webp': '🖼️',
            'mp4': '🎬', 'mp3': '🎵', 'zip': '📁', 'rar': '📁',
        }
        return icons.get(ext, '📎')