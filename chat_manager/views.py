from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import ChatRoom, Message
from .forms import ChatFileUploadForm
from classroom_core.models import Course
from django.contrib.auth.models import User
import json

@login_required
def chat_list(request):
    """Список комнат чата пользователя"""
    rooms = ChatRoom.objects.filter(
        participants=request.user,
        is_active=True
    ).prefetch_related('participants')
    
    # Добавляем последнее сообщение для каждой комнаты
    for room in rooms:
        room.last_message = room.get_last_message()
    
    # Получаем всех пользователей для создания новых чатов (кроме текущего)
    other_users = User.objects.exclude(id=request.user.id).exclude(is_active=False)
    
    return render(request, 'chat_manager/chat_list.html', {
        'rooms': rooms,
        'other_users': other_users
    })

@login_required
def chat_room(request, room_id):
    """Страница конкретной комнаты чата"""
    room = get_object_or_404(ChatRoom, id=room_id, is_active=True)
    
    # Проверяем, есть ли пользователь в комнате
    if not room.participants.filter(id=request.user.id).exists():
        messages.error(request, 'У вас нет доступа к этой комнате чата')
        return redirect('chat_manager:chat_list')
    
    # Получаем последние 50 сообщений (только для первоначальной загрузки)
    messages_qs = Message.objects.filter(room=room).order_by('-timestamp')[:50]
    messages_list = reversed(messages_qs)
    
    # Отмечаем сообщения как прочитанные
    Message.objects.filter(
        room=room,
        user__in=room.participants.exclude(id=request.user.id),
        is_read=False
    ).update(is_read=True)
    
    return render(request, 'chat_manager/chat_room.html', {
        'room': room,
        'messages': messages_list
    })

@login_required
def create_course_chat(request, course_id):
    """Создание чата для курса"""
    course = get_object_or_404(Course, id=course_id)
    
    # Проверяем доступ к курсу
    if not course.can_access(request.user):
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('classroom_core:course_list')
    
    # Проверяем, существует ли уже чат для курса
    existing_room = ChatRoom.objects.filter(
        course=course,
        room_type='course',
        is_active=True
    ).first()
    
    if existing_room:
        return redirect('chat_manager:chat_room', room_id=existing_room.id)
    
    # Создаем новую комнату
    room = ChatRoom.objects.create(
        name=f'Чат курса: {course.title}',
        room_type='course',
        course=course,
        created_by=request.user
    )
    
    # Добавляем всех участников курса
    all_participants = set()
    all_participants.add(course.instructor)
    all_participants.update(course.teaching_assistants.all())
    all_participants.update(course.students.all())
    
    room.participants.set(all_participants)
    
    messages.success(request, 'Чат курса успешно создан')
    return redirect('chat_manager:chat_room', room_id=room.id)

@login_required
def create_private_chat(request, user_id):
    """Создание личного чата с другим пользователем"""
    other_user = get_object_or_404(User, id=user_id)
    
    # Проверяем, что пользователь не пытается создать чат с самим собой
    if other_user == request.user:
        messages.error(request, 'Нельзя создать чат с самим собой')
        return redirect('chat_manager:chat_list')
    
    # Получаем или создаем личный чат
    room = ChatRoom.get_or_create_private_chat(request.user, other_user)
    
    messages.success(request, f'Чат с {other_user.username} успешно создан')
    return redirect('chat_manager:chat_room', room_id=room.id)

@login_required
def search_users(request):
    """Поиск пользователей для создания чата"""
    query = request.GET.get('q', '')
    users = []
    
    if query:
        users = User.objects.filter(
            Q(username__icontains=query) | 
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query)
        ).exclude(id=request.user.id).exclude(is_active=False)[:10]
    
    return render(request, 'chat_manager/user_search_results.html', {
        'users': users,
        'query': query
    })

@login_required
@require_http_methods(["POST"])
def upload_file_to_chat(request, room_id):
    """Загрузка файла в чат"""
    room = get_object_or_404(ChatRoom, id=room_id, is_active=True)
    
    # Проверяем, есть ли пользователь в комнате
    if not room.participants.filter(id=request.user.id).exists():
        return JsonResponse({'error': 'У вас нет доступа к этой комнате чата'}, status=403)
    
    form = ChatFileUploadForm(request.POST, request.FILES)
    
    if form.is_valid():
        content = form.cleaned_data.get('content', '')
        file_attachment = form.cleaned_data['file_attachment']
        
        # Создаем сообщение с файлом
        message = Message.objects.create(
            room=room,
            user=request.user,
            content=content,
            file_attachment=file_attachment
        )
        
        # Возвращаем данные для WebSocket
        response_data = {
            'id': message.id,
            'user_id': request.user.id,
            'username': request.user.username,
            'timestamp': message.timestamp.isoformat(),
            'content': content,
            'has_file': True,
            'is_image': message.is_image(),
            'file_url': message.file_attachment.url if message.file_attachment else None,
            'file_name': message.file_attachment.name.split('/')[-1] if message.file_attachment else None,
            'file_size': message.get_file_size_display(),
            'file_extension': message.get_file_extension(),
        }
        
        return JsonResponse(response_data)
    else:
        return JsonResponse({'error': form.errors}, status=400)

@login_required
def download_message_file(request, message_id):
    """Скачивание файла из сообщения"""
    from django.http import HttpResponse
    from django.shortcuts import get_object_or_404
    import os
    
    message = get_object_or_404(Message, id=message_id)
    
    # Проверяем доступ к комнате чата
    if not message.room.participants.filter(id=request.user.id).exists():
        return HttpResponse('У вас нет доступа к этому файлу', status=403)
    
    if not message.file_attachment:
        return HttpResponse('Файл не найден', status=404)
    
    file_path = message.file_attachment.path
    
    if not os.path.exists(file_path):
        return HttpResponse('Файл не найден на сервере', status=404)
    
    # Открываем и возвращаем файл
    with open(file_path, 'rb') as fh:
        response = HttpResponse(fh.read(), content_type="application/octet-stream")
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response