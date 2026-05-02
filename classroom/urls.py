from django.contrib import admin 
from django.urls import path ,include 
from django.conf import settings 
from django.conf.urls.static import static 

urlpatterns =[
    path('admin/',admin.site.urls ),
    path('accounts/', include('allauth.urls')),
    path('',include('classroom_core.urls',namespace ='classroom_core')),
    path('files/',include('file_manager.urls',namespace ='file_manager')),
    path('chat/', include('chat_manager.urls', namespace='chat_manager')),
] + static(settings.MEDIA_URL ,document_root =settings.MEDIA_ROOT ) + static(settings.STATIC_URL, document_root = settings.STATIC_ROOT)

handler400 = "classroom.error_views.http_400"
handler403 = "classroom.error_views.http_403"
handler404 = "classroom.error_views.http_404"
handler500 = "classroom.error_views.http_500"