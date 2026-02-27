# Chrome Flag Setup for Microphone Access (No ngrok)

Use the Chrome "Insecure origins" flag so microphone works when opening the call page over HTTP (same LAN). No ngrok or HTTPS required.

## Prerequisites
- Both PCs on the **same network** (e.g. same Wi‑Fi)
- Chrome installed on the PC that will use the mic

---

## Step 1: Get Host IP

**On the PC where Django runs**, find its IP address:

- **Linux:** `hostname -I` or `ip addr`
- **Windows:** `ipconfig` → look for IPv4 Address
- Example: `192.168.1.100`

---

## Step 2: Start Django

On the host PC:

```bash
cd /home/machinist/Desktop/EMS/employee_management_system
python manage.py runserver 0.0.0.0:8000
```

Keep this running.

---

## Step 3: Configure Chrome Flag

**On the PC where you will use the microphone** (can be the same as host):

1. Open **Chrome**
2. Go to: `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
3. In **"Insecure origins treated as secure"**, add:
   ```
   http://HOST_IP:8000
   ```
   Replace `HOST_IP` with the IP from Step 1 (e.g. `http://192.168.1.100:8000`)
4. Set the dropdown to **Enabled**
5. Click **Relaunch**

---

## Step 4: Open Call Page

1. After Chrome restarts, go to:
   ```
   http://HOST_IP:8000/messaging/call/
   ```
2. Log in as alice, bob, or john
3. Microphone should work (browser will prompt to allow)

---

## Important
- The URL in the flag **must match** the URL you open in the browser exactly
- If your host IP changes (e.g. new network), update the flag with the new IP
- This is for **local development/testing** only; use HTTPS in production
