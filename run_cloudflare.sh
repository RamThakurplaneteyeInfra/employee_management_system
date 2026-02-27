#!/bin/bash
# Run Cloudflare Tunnel to expose Django on HTTPS
# Usage: ./run_cloudflare.sh
# 1. Start Django first: python manage.py runserver 0.0.0.0:8000
# 2. Run this script in another terminal
# 3. Copy the https://xxx.trycloudflare.com URL from output
# 4. Add to .env: CLOUDFLARE_TUNNEL_ORIGIN=https://your-url.trycloudflare.com
# 5. Restart Django
# 6. Open the HTTPS URL in browser - mic/camera will work on any PC

echo "Starting Cloudflare Tunnel (ensure Django is running on port 8000)..."
echo ""
echo "After it starts, copy the 'https://xxx.trycloudflare.com' URL, add to .env as:"
echo "  CLOUDFLARE_TUNNEL_ORIGIN=https://your-url.trycloudflare.com"
echo ""
echo "Then restart Django and open the HTTPS URL in browser."
echo ""

# Use local binary if cloudflared not in PATH
if command -v cloudflared &>/dev/null; then
  cloudflared tunnel --url http://localhost:8000
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [ -x "$SCRIPT_DIR/cloudflared" ]; then
    "$SCRIPT_DIR/cloudflared" tunnel --url http://localhost:8000
  else
    echo "Error: cloudflared not found. Install it or run: wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O $SCRIPT_DIR/cloudflared && chmod +x $SCRIPT_DIR/cloudflared"
    exit 1
  fi
fi
