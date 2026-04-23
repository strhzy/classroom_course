from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_list, name='chat_list'),
    path('room/<int:room_id>/', views.chat_room, name='chat_room'),
    path('course/<int:course_id>/create/', views.create_course_chat, name='create_course_chat'),
    path('private/<int:user_id>/create/', views.create_private_chat, name='create_private_chat'),
    path('search/', views.search_users, name='search_users'),
    path('room/<int:room_id>/upload/', views.upload_file_to_chat, name='upload_file'),
    path('message/<int:message_id>/download/', views.download_message_file, name='download_file'),
]