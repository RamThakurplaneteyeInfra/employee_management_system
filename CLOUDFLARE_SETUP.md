# Cloudflare Tunnel Setup for Audio/Video Call (HTTPS)

Use Cloudflare Tunnel to get HTTPS so microphone and camera work from any PC without Chrome flags.

## Prerequisites

- Django running on port 8000
- cloudflared installed

## Install cloudflared

**Ubuntu/Debian:**
```bash
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

**Or download from:** https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

## Steps

### 1. Start Django

```bash
cd /home/machinist/Desktop/EMS/employee_management_system
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

Keep this terminal open.

### 2. Start Cloudflare Tunnel

In a **new terminal**:

```bash
cd /home/machinist/Desktop/EMS/employee_management_system
./run_cloudflare.sh
```

Or run directly:
```bash
cloudflared tunnel --url http://localhost:8000
```

### 3. Copy the HTTPS URL

From the cloudflared output, copy the URL like:
```
https://abc-xyz-123.trycloudflare.com
```

### 4. Add to .env

Edit `.env` and set:
```
CLOUDFLARE_TUNNEL_ORIGIN=https://abc-xyz-123.trycloudflare.com
```
(Use your actual URL from step 3.)

### 5. Restart Django

Stop Django (Ctrl+C in the first terminal), then start again:
```bash
python manage.py runserver 0.0.0.0:8000
```

### 6. Open the call page

In any browser, on any PC:
```
https://abc-xyz-123.trycloudflare.com/messaging/call/
```

Log in as alice or bob. Microphone and camera will work (no Chrome flag needed).

## Note

The trycloudflare.com URL changes each time you run cloudflared. If you restart cloudflared:
1. Copy the new URL
2. Update CLOUDFLARE_TUNNEL_ORIGIN in .env
3. Restart Django
