#!/bin/bash
# Установка бота регистрации/автовеба на чистый сервер Timeweb Cloud (Ubuntu 24.04). Запускается один раз при создании сервера.
# Перед запуском должен быть файл /opt/bot.env с переменными бота (его пишет cloud-init сервера).
# Без Docker: Docker Hub недоступен с российских серверов. Бот работает как служба systemd «bot».
set -e
. /opt/bot.env
# ход установки виден в описании бота на языке zu (людям оно не показывается); в конце очищается
report() { curl -s -m 15 "https://api.telegram.org/bot$BOT_TOKEN/setMyShortDescription" --data-urlencode "short_description=$1" -d language_code=zu >/dev/null || true; }
trap 'report "install failed at line $LINENO: $(tail -c 80 /var/log/bot-install.log | tr "\n" " ")"' ERR
report "install: start"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y && apt-get install -y git curl python3-venv debian-keyring debian-archive-keyring apt-transport-https gnupg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --batch --yes --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
apt-get update -y && apt-get install -y caddy
report "install: packages ok"
IP=$(curl -s https://api.ipify.org)
HOST="$(echo $IP | tr . -).sslip.io"
# HTTPS с настоящим сертификатом (Let's Encrypt) на адрес вида 1-2-3-4.sslip.io
printf '%s {\n  reverse_proxy 127.0.0.1:8080\n}\n' "$HOST" > /etc/caddy/Caddyfile
systemctl restart caddy
# код: из GitHub, а если GitHub недоступен, из архива, который cloud-init положил в $SRC
[ -d /opt/a ] || timeout 90 git clone -q -b claude/busy-noether-jpca9m https://github.com/olgapuzanova0311-art/a.git /opt/a || { rm -rf /opt/a; mkdir -p /opt/a && cp -r "$SRC/bot" /opt/a/; }
report "install: code $( [ -d /opt/a/.git ] && echo git || echo archive )"
grep -q '^PUBLIC_URL=' /opt/bot.env || echo "PUBLIC_URL=https://$HOST" >> /opt/bot.env
grep -q '^WEBHOOK=' /opt/bot.env || echo "WEBHOOK=1" >> /opt/bot.env
mkdir -p /data
python3 -m venv /opt/venv && /opt/venv/bin/pip install -q -r /opt/a/bot/requirements.txt
report "install: python ok, host $HOST"
cat > /etc/systemd/system/bot.service <<'EOS'
[Unit]
Description=Telegram bot @aikomandaweb_bot
After=network-online.target
Wants=network-online.target
[Service]
WorkingDirectory=/opt/a/bot
EnvironmentFile=/opt/bot.env
ExecStart=/opt/venv/bin/python main.py
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOS
systemctl daemon-reload && systemctl enable --now bot
# обновление бота: /opt/update.sh (подтягивает ветку, ставит зависимости, перезапускает)
cat > /opt/update.sh <<'EOS'
#!/bin/bash
set -e
cd /opt/a && git pull -q && /opt/venv/bin/pip install -q -r /opt/a/bot/requirements.txt && systemctl restart bot
EOS
chmod +x /opt/update.sh
# автообновление: раз в 2 минуты проверяем новые коммиты в ветке (только если код из git)
if [ -d /opt/a/.git ]; then cat > /etc/cron.d/bot-update <<'EOS'
*/2 * * * * root cd /opt/a && git fetch -q && [ "$(git rev-parse HEAD)" != "$(git rev-parse @{u})" ] && /opt/update.sh >> /var/log/bot-update.log 2>&1
EOS
fi
sleep 20
report "install: done, bot $(systemctl is-active bot)"
