"""
Optional JWT authentication for WebSocket or API use.
The Real-Time Chat WebSocket (/ws/chat/) uses session-based auth (scope["user"] from AuthMiddlewareStack);
this module is not used there. Kept for optional JWT support (e.g. query ?token= or Authorization: Bearer).
"""
import logging
from urllib.parse import parse_qs

from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


def get_user_from_scope(scope):
    """
    Resolve authenticated user from WebSocket scope using JWT.
    Token can be in query string (?token=...) or in headers (Authorization: Bearer <token>).
    Returns (user, error_message). user is None if invalid; error_message is set for reject.
    """
    token = None

    # Query string: ?token=<access_token>
    query_string = scope.get("query_string", b"").decode("utf-8")
    if query_string:
        parsed = parse_qs(query_string)
        tokens = parsed.get("token", [])
        if tokens:
            token = tokens[0].strip() if isinstance(tokens[0], str) else None

    # Header: Authorization: Bearer <token>
    if not token and "headers" in scope:
        for name, value in scope["headers"]:
            if name.lower() == b"authorization":
                val = value.decode("utf-8").strip()
                if val.lower().startswith("bearer "):
                    token = val[7:].strip()
                break

    if not token:
        return None, "Missing token (use ?token=<access_token> or Authorization: Bearer <token>)"

    try:
        from rest_framework_simplejwt.tokens import AccessToken
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
    except ImportError:
        logger.warning("rest_framework_simplejwt not installed; chat WebSocket JWT auth disabled.")
        return None, "JWT authentication not available"

    try:
        access = AccessToken(token)
        user_id = access.get("user_id")
        if not user_id:
            return None, "Invalid token payload"
        User = get_user_model()
        user = User.objects.get(pk=user_id)
        return user, None
    except (InvalidToken, TokenError) as e:
        logger.debug("Chat WebSocket JWT invalid: %s", e)
        return None, "Invalid or expired token"
    except User.DoesNotExist:
        return None, "User not found"
