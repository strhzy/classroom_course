from django.db import models
from django.contrib.auth.models import User
from classroom_core.models import Course

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
        # Найти существующий чат
        rooms = cls.objects.filter(
            room_type='private',
            is_active=True,
            participants=user1
        ).filter(participants=user2)
        
        if rooms.exists():
            return rooms.first()
        
        # Создать новый чат
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
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        indexes = [
            models.Index(fields=['room', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.content[:50]}"
    
    def mark_as_read(self):
        """Отметить сообщение как прочитанное"""
        self.is_read = True
        self.save(update_fields=['is_read'])