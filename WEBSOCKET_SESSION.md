# WebSocket Connection (Session Authentication Only)

WebSocket connections use **Django session cookies only**. No JWT or tokens.

## Requirements for Cross-Origin

1. **Backend** (this project): `ems/asgi.py` uses `SessionMiddlewareStack` + `AuthMiddlewareStack`.
2. **Session cookie** must allow cross-origin:
   - `SESSION_COOKIE_SAMESITE = "None"`
   - `SESSION_COOKIE_SECURE = True` (required when SameSite=None → **HTTPS only**)
3. **CORS**: `CORS_ALLOW_CREDENTIALS = True` (already set).
4. **ALLOWED_HOSTS**: Include the frontend origin (e.g. `http://192.168.42.107:3000`).
5. **User must be logged in** to the backend first (login sets `sessionid` cookie).

For **HTTP in development**, cross-origin cookies will not work (SameSite=None requires Secure). Use:
- Same-origin setup (proxy frontend through backend), or
- Local HTTPS (e.g. ngrok, mkcert).

---

## Frontend Connection Code

### Vanilla JavaScript / React

```javascript
// Build WebSocket URL (same scheme as page: ws for http, wss for https)
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const backendHost = 'your-backend-host.com';  // or 192.168.42.107
const port = window.location.protocol === 'https:' ? '' : ':8000';
const wsUrl = `${protocol}//${backendHost}${port}/ws/notifications/`;

const ws = new WebSocket(wsUrl);

ws.onopen = () => {
  console.log('WebSocket connected (session auth)');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'notification') {
    console.log('Notification:', data.title, data.message);
  } else if (data.type === 'pong') {
    console.log('Pong');
  }
};

ws.onerror = (err) => {
  console.error('WebSocket error:', err);
};

ws.onclose = (event) => {
  // 4001 = anonymous user (not logged in)
  if (event.code === 4001) {
    console.log('Not authenticated – please log in');
  }
  console.log('WebSocket closed:', event.code, event.reason);
};

// Optional: send ping for heartbeat
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping' }));
  }
}, 30000);
```

**Important:** The browser sends the `sessionid` cookie automatically. No `Authorization` header or query param.

---

## Endpoints

| Path                    | Purpose                      |
|-------------------------|------------------------------|
| `ws/notifications/`     | User-specific notifications  |

Requires an authenticated session. Anonymous connections receive close code `4001`.
