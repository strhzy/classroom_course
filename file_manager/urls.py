from django.urls import path 
from . import views 

app_name ='file_manager'

urlpatterns =[
path('',views.file_list ,name ='file_list'),
path('upload/',views.file_upload ,name ='file_upload'),
path('<int:file_id>/',views.file_detail ,name ='file_detail'),
path('<int:file_id>/download/',views.file_download ,name ='file_download'),
path('<int:file_id>/preview/',views.file_preview ,name ='file_preview'),
path('<int:file_id>/edit/',views.file_edit ,name ='file_edit'),
path('<int:file_id>/delete/',views.file_delete ,name ='file_delete'),
path('<int:file_id>/version/',views.file_version_create ,name ='file_version_create'),
path('folder/create/',views.folder_create ,name ='folder_create'),
path('<int:file_id>/favorite/',views.favorite_toggle ,name ='favorite_toggle'),
path('<int:file_id>/comment/',views.file_comment_create ,name ='file_comment_create'),
path('comment/<int:comment_id>/delete/',views.file_comment_delete ,name ='file_comment_delete'),
path('categories/',views.category_list ,name ='category_list'),
path('categories/create/',views.category_create ,name ='category_create'),
path('tags/',views.tag_list ,name ='tag_list'),
path('tags/create/',views.tag_create ,name ='tag_create'),
path('activity/',views.activity_log ,name ='activity_log'),
path('api/storage-quota/',views.get_storage_quota ,name ='storage_quota_api'),
path('oauth/yandex/start/', views.yandex_oauth_start, name='yandex_oauth_start'),
path('oauth/yandex/callback/', views.yandex_oauth_callback, name='yandex_oauth_callback'),
path('oauth/yandex/disconnect/', views.yandex_disconnect, name='yandex_disconnect'),
path('yandex/picker/', views.yandex_file_picker, name='yandex_picker'),
path('<int:file_id>/yandex/export/', views.yandex_export_file, name='yandex_export_file'),
path('download-all/', views.download_all_files_archive, name='download_all_files_archive'),
path('favorite-collections/create/', views.favorite_collection_create, name='favorite_collection_create'),
path('<int:file_id>/favorite-collections/add/', views.favorite_collection_add_file, name='favorite_collection_add_file'),
path('workspaces/create/', views.workspace_create, name='workspace_create'),
path('<int:file_id>/workspaces/add/', views.workspace_add_file, name='workspace_add_file'),
path('backups/compare/', views.backup_compare, name='backup_compare'),
]