import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ems.settings")

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.sessions import SessionMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
django_Asgi_app=get_asgi_application()

import ems.routing as routing

# WebSocket: session-only auth (no JWT/tokens).
# Cookies sent automatically by browser for same-site or cross-origin (SameSite=None; Secure).
application = ProtocolTypeRouter({

    "http": django_Asgi_app,

    "websocket": AuthMiddlewareStack(

        URLRouter(

            routing.websocket_urlpatterns

        )

    ),

}) 