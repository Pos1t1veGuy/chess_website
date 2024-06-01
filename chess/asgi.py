import os, sys
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from .consumers import QueueConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chess.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path('ws/queue/', QueueConsumer.as_asgi()),
        ])
    ),
})