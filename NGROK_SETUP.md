# ngrok Setup for Audio Call (Microphone Access)

Use ngrok to run the call page over HTTPS so microphone access works from any PC (fixes "navigator.mediaDevices undefined" error).

## Steps

### 1. Install ngrok
- Download from https://ngrok.com/download
- Or: `sudo apt install ngrok` (Linux)

### 2. Start Django
```bash
python manage.py runserver 0.0.0.0:8000
```

### 3. Start ngrok (in a new terminal)
```bash
./run_ngrok.sh
```
Or: `ngrok http 8000`

### 4. Copy the HTTPS URL
From ngrok output, copy the **https** URL (e.g. `https://abc123.ngrok-free.app`).

### 5. Add to .env
Edit `.env` and set:
```
NGROK_ORIGIN=https://YOUR-NGROK-URL.ngrok-free.app
```
(Use your actual ngrok URL, no trailing slash.)

### 6. Restart Django
Stop Django (Ctrl+C) and start again:
```bash
python manage.py runserver 0.0.0.0:8000
```

### 7. Open call page from any PC
- On the same machine: open the ngrok **https** URL in browser
- From another PC/phone: open the same ngrok **https** URL
- Go to: `https://YOUR-NGROK-URL.ngrok-free.app/messaging/call/`
- Log in as alice or bob
- Microphone access will work (browser will prompt)

## Testing from Two Devices
- **PC 1 (Django host):** Open ngrok URL, log in as alice, call bob
- **PC 2 (other device):** Open same ngrok URL, log in as bob, accept the call
- Both will hear each other over the call
