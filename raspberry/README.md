# Raspberry Pi de la CC-Printer A1 (Klipper + Moonraker + Fluidd)

Copia de todo lo que corre en la Pi, para rearmarla desde cero si se rompe la SD.
Las copias de esta carpeta son las **maestras**. Cuando las edites acá, copialas a la Pi.

> **Después de un `SAVE_CONFIG` (PID, Z offset, etc.) traé primero el `printer.cfg` de la Pi**
> (`~/printer_data/config/printer.cfg`). Si no lo hacés, al pisarlo con la copia de acá
> se pierde el bloque `#*#` que guarda Klipper.

## Qué hay en cada carpeta

| Carpeta | Destino en la Pi |
|---|---|
| `klipper/printer.cfg`, `klipper/macros.cfg` | `~/printer_data/config/` |
| `klipper/mcu-atmega2560.config` | `~/klipper/.config` (firmware del Mega) |
| `klipper/marlin_backup_M503_2026-11-16.txt` | Ajustes de Marlin antes del cambio (solo referencia) |
| `moonraker/moonraker.conf` | `~/printer_data/config/` |
| `nginx/conf.d/*`, `nginx/snippets/*`, `nginx/sites-available/fluidd` | `/etc/nginx/...` (misma estructura) |
| `systemd/*.service` | `/etc/systemd/system/` |
| `systemd/printer_data/*.env` | `~/printer_data/systemd/` |
| `cc-cam/` | `~/cc-cam/` (servidor de la cámara + script de la ruta secreta) |
| `pinout_pi4_ccpa1.*`, `_gen/` | Hoja de pines de la Pi (ADXL345, ventilador) |

## Lo que NO está en el repo (secretos y estado)

- **`.secrets`** (en la PC, fuera de git): usuario y contraseña de la Pi, token de la API de Cloudflare y clave del Wi-Fi.
- **`/etc/cloudflared/impresora.env`**: token del túnel (`TUNNEL_TOKEN=...`). Lo volvés a sacar del panel de Cloudflare.
- **Ruta secreta de la cámara**: el `moonraker.conf` del repo dice `cam-SECRETO`. La ruta real la genera `rotar_link_camara.sh`, que también crea `/etc/nginx/snippets/cc-webcam-secret.conf`.
- **`~/printer_data/database/moonraker-sql.db`**: usuarios de Fluidd e historial de impresiones. Tiene los hashes de las contraseñas, así que si querés backup, guardalo aparte.

## Rearmado desde cero

Probado con Raspberry Pi OS 64-bit (Debian 13 trixie), hostname `ImpresoraChori`, usuario `chori`.
Las rutas de los archivos asumen `/home/chori`.

### 0. Paquetes y carpetas

```bash
sudo apt update
sudo apt install -y git python3-venv python3-dev libffi-dev build-essential \
    gcc-avr avr-libc binutils-avr avrdude nginx unzip curl python3-picamera2
mkdir -p ~/printer_data/{config,logs,gcodes,systemd,comms,database}
chmod o+x ~          # nginx (www-data) tiene que poder leer ~/fluidd
```

Wi-Fi: perfil `Chori-NET` con NetworkManager y el ahorro de energía apagado:
`sudo nmcli con mod Chori-NET 802-11-wireless.powersave 2`.

### 1. Klipper

Se instala a mano porque `scripts/install-debian.sh` todavía usa `~/printer.cfg`.

```bash
git clone https://github.com/Klipper3d/klipper ~/klipper
git -C ~/klipper checkout 29d4ec2d6        # versión probada: v0.13.0-827
python3 -m venv ~/klippy-env
~/klippy-env/bin/pip install -r ~/klipper/scripts/klippy-requirements.txt
cp klipper/printer.cfg klipper/macros.cfg ~/printer_data/config/
cp systemd/printer_data/klipper.env ~/printer_data/systemd/
sudo cp systemd/klipper.service /etc/systemd/system/
```

Firmware del Mega (clon CH340 → `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0`):

```bash
cp klipper/mcu-atmega2560.config ~/klipper/.config   # atmega2560, 16 MHz, 250000 baudios
cd ~/klipper && make
sudo systemctl stop klipper
make flash FLASH_DEVICE=/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0
```

Para volver a Marlin: flashear `firmware-builds/2026-11-12-v3/firmware-v3.hex` con avrdude
(`-p atmega2560 -c wiring -b 115200 -D`), con el servicio klipper parado.

### 2. Moonraker

```bash
git clone https://github.com/Arksine/moonraker ~/moonraker
git -C ~/moonraker checkout b559b9a         # versión probada: v0.11.0-4
cp moonraker/moonraker.conf ~/printer_data/config/
~/moonraker/scripts/install-moonraker.sh -d ~/printer_data
```

El instalador crea `moonraker.service`, `moonraker.env` y las reglas de polkit.
Las copias de `systemd/` son solo de referencia.

### 3. Fluidd

```bash
mkdir -p ~/fluidd && cd ~/fluidd
curl -L -o fluidd.zip https://github.com/fluidd-core/fluidd/releases/download/v1.38.0/fluidd.zip
unzip fluidd.zip && rm fluidd.zip
```

### 4. nginx

```bash
sudo cp nginx/conf.d/*.conf /etc/nginx/conf.d/
sudo cp nginx/snippets/*.conf /etc/nginx/snippets/
sudo cp nginx/sites-available/fluidd /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/fluidd /etc/nginx/sites-enabled/fluidd
sudo rm -f /etc/nginx/sites-enabled/default
sudo touch /etc/nginx/snippets/cc-webcam-secret.conf   # lo llena el paso 5
sudo nginx -t && sudo systemctl restart nginx
```

Cómo funciona:
- **`:80`** es la red de casa. Moonraker la trata como confiable (`192.168.0.0/24`), así que no pide login.
- **`127.0.0.1:8081`** es la entrada del túnel de Cloudflare. Le pasa a Moonraker la IP real de internet (`cc_tunnel_map.conf`), así que **siempre** pide login. Además bloquea `/webcam/`.

### 5. Cámara (IMX219 NoIR por CSI)

```bash
mkdir -p ~/cc-cam && cp cc-cam/* ~/cc-cam/ && chmod +x ~/cc-cam/rotar_link_camara.sh
sudo cp systemd/cc-cam.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now klipper cc-cam
sudo ~/cc-cam/rotar_link_camara.sh     # genera la ruta secreta /cam-<token>/ y reinicia moonraker
```

`cam_server.py` usa el tuning `imx219_noir.json`. Sin ese tuning la imagen sale magenta.
Volvé a correr `rotar_link_camara.sh` cada vez que quieras invalidar los links viejos de la cámara.

### 6. Túnel de Cloudflare (`impresora.cc-lab.space`)

```bash
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' \
    | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install -y cloudflared

sudo mkdir -p /etc/cloudflared
sudo install -m 600 /dev/null /etc/cloudflared/impresora.env
sudo nano /etc/cloudflared/impresora.env    # una línea: TUNNEL_TOKEN=<token del panel de Cloudflare>
sudo cp systemd/cloudflared-impresora.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now cloudflared-impresora
```

El túnel se administra desde el panel de Cloudflare. Ahí están la regla `impresora.cc-lab.space → http://127.0.0.1:8081`
y el CNAME, no en la Pi.

### 7. Después de instalar

- Crear al menos un usuario en **Fluidd → Settings → Authentication**, desde la red de casa. Sin usuario, nadie puede entrar desde internet.
- Pendiente para el ADXL345: activar SPI (`dtparam=spi=on` en `/boot/firmware/config.txt`).
