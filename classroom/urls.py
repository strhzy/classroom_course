from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

_core_urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("classroom_core.urls", namespace="classroom_core")),
    path("files/", include("file_manager.urls", namespace="file_manager")),
    path("chat/", include("chat_manager.urls", namespace="chat_manager")),
]

if settings.DEBUG:
    urlpatterns = _core_urlpatterns + static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    ) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    urlpatterns = list(_core_urlpatterns)
    if getattr(settings, "SERVE_MEDIA_FROM_DJANGO", False):
        urlpatterns += [
            re_path(
                r"^media/(?P<path>.*)$",
                serve,
                {"document_root": settings.MEDIA_ROOT},
            ),
        ]

handler400 = "classroom.error_views.http_400"
handler403 = "classroom.error_views.http_403"
handler404 = "classroom.error_views.http_404"
handler500 = "classroom.error_views.http_500"
