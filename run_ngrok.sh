#!/bin/bash
# Run ngrok to expose Django on HTTPS for audio call (microphone access).
# Usage:
#   1. Start Django: python manage.py runserver 0.0.0.0:8000
#   2. Run this: ./run_ngrok.sh
#   3. Copy the HTTPS URL from ngrok output (e.g. https://abc123.ngrok-free.app)
#   4. Add to .env: NGROK_ORIGIN=https://abc123.ngrok-free.app
#   5. Restart Django
#   6. Open the ngrok HTTPS URL in browser from any PC

echo "Starting ngrok on port 8000..."
echo "After ngrok starts, copy the HTTPS URL and add to .env:"
echo "  NGROK_ORIGIN=https://YOUR-NGROK-URL.ngrok-free.app"
echo "Then restart Django and open the ngrok URL in your browser."
echo ""
ngrok http 8000
