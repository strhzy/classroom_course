from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver 
from django.contrib.auth.models import User 
from .models import UserProfile 
from chat_manager.models import ChatRoom
from .models import Course

@receiver(post_save ,sender =User )
def create_user_profile(sender ,instance ,created ,**kwargs ):
    if created :
        UserProfile.objects.create(user =instance )

@receiver(post_save ,sender =User )
def save_user_profile(sender ,instance ,**kwargs ):
    instance.profile.save()

@receiver(post_save, sender=Course)
def create_course_chat(sender, instance, created, **kwargs):
    """
    Автоматическое создание чата при создании курса
    """
    if created:
        # Проверяем, нет ли уже чата для этого курса
        existing_chat = ChatRoom.objects.filter(course=instance, room_type='course').first()
        if not existing_chat:
            # Создаем чат комнату для курса
            room = ChatRoom.objects.create(
                name=f'Чат курса: {instance.title}',
                room_type='course',
                course=instance,
                created_by=instance.instructor
            )
            
            # Добавляем всех участников курса
            participants = set()
            participants.add(instance.instructor)
            participants.update(instance.teaching_assistants.all())
            participants.update(instance.students.all())
            room.participants.set(participants)

@receiver(m2m_changed, sender=Course.students.through)
def update_course_chat_on_student_change(sender, instance, action, pk_set, **kwargs):
    """
    Обновление чата при добавлении/удалении студентов из курса
    """
    if action in ['post_add', 'post_remove']:
        # Находим чат курса
        chat_room = ChatRoom.objects.filter(course=instance, room_type='course').first()
        
        if chat_room:
            if action == 'post_add':
                # Добавляем новых студентов в чат
                chat_room.participants.add(*pk_set)
            elif action == 'post_remove':
                # Удаляем студентов из чата
                chat_room.participants.remove(*pk_set)

@receiver(m2m_changed, sender=Course.teaching_assistants.through)
def update_course_chat_on_ta_change(sender, instance, action, pk_set, **kwargs):
    """
    Обновление чата при добавлении/удалении помощников преподавателя
    """
    if action in ['post_add', 'post_remove']:
        # Находим чат курса
        chat_room = ChatRoom.objects.filter(course=instance, room_type='course').first()
        
        if chat_room:
            if action == 'post_add':
                # Добавляем новых помощников в чат
                chat_room.participants.add(*pk_set)
            elif action == 'post_remove':
                # Удаляем помощников из чата
                chat_room.participants.remove(*pk_set)

@receiver(m2m_changed, sender=Course.student_groups.through)
def update_course_chat_on_group_change(sender, instance, action, pk_set, **kwargs):
    """
    Обновление чата при добавлении/удалении групп студентов из курса
    """
    if action == 'post_add':
        # Находим чат курса
        chat_room = ChatRoom.objects.filter(course=instance, room_type='course').first()
        
        if chat_room:
            # Добавляем всех студентов из новых групп в чат
            from classroom_core.models import StudentGroup
            for group_id in pk_set:
                try:
                    group = StudentGroup.objects.get(id=group_id)
                    for profile in group.students.all():
                        chat_room.participants.add(profile.user)
                except StudentGroup.DoesNotExist:
                    continue