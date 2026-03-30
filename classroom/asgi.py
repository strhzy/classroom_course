import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path
from channels.auth import AuthMiddlewareStack

import chat_manager.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'classroom.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chat_manager.routing.websocket_urlpatterns
        )
    ),
})