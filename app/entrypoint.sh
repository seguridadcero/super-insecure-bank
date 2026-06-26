#!/bin/sh
set -eu

export OPENSSL_CONF=/etc/ssl/openssl-sib.cnf

mkdir -p /app/data/certs /run/nginx

if [ ! -f /app/data/certs/sib-selfsigned.crt ] || [ ! -f /app/data/certs/sib-selfsigned.key ]; then
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout /app/data/certs/sib-selfsigned.key \
    -out /app/data/certs/sib-selfsigned.crt \
    -days 3650 \
    -subj "/CN=superinsecurebank.local" >/dev/null 2>&1
fi

echo ""
echo "=============================================="
echo " Super Insecure Bank is running"
echo "=============================================="
echo ""
echo "Access URLs:"
echo ""
echo "  Local:"
echo "    http://127.0.0.1:5080"
echo "    https://127.0.0.1:5443"
echo ""
echo "  From Burp / another VM / LAN:"
if [ -n "${SIB_HOST_IP:-}" ]; then
  echo "    http://${SIB_HOST_IP}:5080"
  echo "    https://${SIB_HOST_IP}:5443"
else
  echo "    http://<YOUR-HOST-IP>:5080"
  echo "    https://<YOUR-HOST-IP>:5443"
fi
echo ""
echo "Do not use Docker internal IPs such as 172.x.x.x for browser or Burp access."
echo "To find your host IP on Kali/Linux, run:"
echo "  ip -4 addr show eth0"
echo ""
echo "HTTPS is intentionally weak for the lab:"
echo "  - self-signed certificate"
echo "  - TLS 1.1 enabled"
echo "  - legacy CBC/SHA and 3DES cipher configured when available"
echo "=============================================="
echo ""

python /app/app.py &
FLASK_PID="$!"

# Wait for Flask before starting Nginx
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:5000/login >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

nginx -c /etc/nginx/nginx.conf -g "daemon off;" &
NGINX_PID="$!"

trap 'kill "$FLASK_PID" "$NGINX_PID" 2>/dev/null || true' INT TERM
wait "$NGINX_PID"
