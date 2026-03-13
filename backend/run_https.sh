#!/usr/bin/env bash
# Run FastAPI with HTTPS so Safari can use geolocation/camera/compass.
# Generates a self-signed cert on first run. Use https://<Pi-IP>:8443 and accept the certificate warning.

set -e
cd "$(dirname "$0")"
CERTS_DIR=certs
KEY="$CERTS_DIR/key.pem"
CERT="$CERTS_DIR/cert.pem"

mkdir -p "$CERTS_DIR"
if [ ! -f "$KEY" ] || [ ! -f "$CERT" ]; then
  echo "[HTTPS] Generating self-signed certificate (valid 365 days)..."
  openssl req -x509 -newkey rsa:2048 -keyout "$KEY" -out "$CERT" -days 365 -nodes \
    -subj "/CN=horizon-air/O=HorizonAir/C=US"
fi

echo "[HTTPS] HorizonAir: open https://<Pi-IP>:8443 in Safari and accept the certificate to use GPS/camera."
exec uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile="$KEY" --ssl-certfile="$CERT"
