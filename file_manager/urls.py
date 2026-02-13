from django.urls import path
from . import views

app_name = 'file_manager'

urlpatterns = [
    path('', views.courses_overview, name='file_list'),
    path('upload/', views.file_upload, name='file_upload'),
    path('all/', views.file_list, name='file_list_all'),
    path('<int:file_id>/', views.file_detail, name='file_detail'),
    path('<int:file_id>/download/', views.file_download, name='file_download'),
    path('<int:file_id>/preview/', views.file_preview, name='file_preview'),
    path('<int:file_id>/edit/', views.file_edit, name='file_edit'),
    path('<int:file_id>/delete/', views.file_delete, name='file_delete'),
    path('<int:file_id>/version/', views.file_version_create, name='file_version_create'),
    path('folder/create/', views.folder_create, name='folder_create'),
    path('<int:file_id>/favorite/', views.favorite_toggle, name='favorite_toggle'),
    path('<int:file_id>/comment/', views.file_comment_create, name='file_comment_create'),
    path('comment/<int:comment_id>/delete/', views.file_comment_delete, name='file_comment_delete'),
    path('courses/', views.courses_overview, name='course_list'),
    path('courses/<int:course_id>/', views.course_files, name='course_files'),
]