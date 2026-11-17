#!/bin/bash
# CC-Printer A1 - genera/cambia la direccion secreta de la camara.
# Desde internet la camara solo se sirve en /cam-<secreto>/ ; Fluidd recibe esa
# direccion de Moonraker, que solo se la da a usuarios logueados.
# Si el link se filtro (o queres invalidar todos los links viejos):
#     sudo ~/cc-cam/rotar_link_camara.sh      y despues F5 en Fluidd.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Correlo con sudo: sudo $0" >&2; exit 1; }

CONF=/home/chori/printer_data/config/moonraker.conf
SNIP=/etc/nginx/snippets/cc-webcam-secret.conf
TOK=$(openssl rand -hex 16)   # 128 bits: imposible de adivinar

cp -a "$CONF" "$CONF.bak-camlink"
if [ -f "$SNIP" ]; then cp -a "$SNIP" "$SNIP.bak"; fi

cat > "$SNIP.tmp" <<NGINX
# Generado por ~/cc-cam/rotar_link_camara.sh - la ruta es secreta, no la compartas.
# Para cambiarla: sudo ~/cc-cam/rotar_link_camara.sh
location /cam-$TOK/ {
    access_log off;                      # que la ruta no quede en los logs
    proxy_hide_header Cache-Control;
    add_header Cache-Control "no-store, private" always;   # Cloudflare no la guarda en cache
    add_header X-Robots-Tag "noindex, nofollow" always;
    postpone_output 0;
    proxy_buffering off;
    proxy_ignore_headers X-Accel-Buffering;
    proxy_pass http://mjpgstreamer1/;
}
NGINX
chmod 640 "$SNIP.tmp"
mv "$SNIP.tmp" "$SNIP"

if ! nginx -t -q; then
    echo "nginx -t fallo; dejo todo como estaba" >&2
    if [ -f "$SNIP.bak" ]; then mv "$SNIP.bak" "$SNIP"; else rm -f "$SNIP"; fi
    exit 1
fi

sed -i -E "s#^(stream_url:).*#\1 /cam-$TOK/stream.mjpg#; s#^(snapshot_url:).*#\1 /cam-$TOK/snapshot.jpg#" "$CONF"
chown chori:chori "$CONF"
systemctl reload nginx
systemctl restart moonraker
rm -f "$SNIP.bak"
echo "Listo: la camara tiene direccion nueva y los links viejos dejaron de andar. Recarga Fluidd (F5)."
