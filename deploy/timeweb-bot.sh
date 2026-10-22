#!/bin/bash
# Установка бота регистрации/автовеба на чистый сервер Timeweb Cloud (Ubuntu). Запускается один раз при создании сервера.
# Перед запуском подставляются: __GH_TOKEN__ (доступ к репозиторию) и файл /opt/bot.env (переменные бота).
set -e
apt-get update -y && apt-get install -y docker.io git curl debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
apt-get update -y && apt-get install -y caddy
IP=$(curl -s https://api.ipify.org)
HOST="$(echo $IP | tr . -).sslip.io"
# HTTPS с настоящим сертификатом (Let's Encrypt) на адрес вида 1-2-3-4.sslip.io
printf '%s {\n  reverse_proxy 127.0.0.1:8080\n}\n' "$HOST" > /etc/caddy/Caddyfile
systemctl restart caddy
git clone -b claude/busy-noether-jpca9m https://x-access-token:__GH_TOKEN__@github.com/olgapuzanova0311-art/a.git /opt/a
echo "PUBLIC_URL=https://$HOST" >> /opt/bot.env
echo "WEBHOOK=1" >> /opt/bot.env
mkdir -p /opt/data
docker build -t bot /opt/a/bot
docker run -d --name bot --restart always --env-file /opt/bot.env -v /opt/data:/data -p 127.0.0.1:8080:8080 bot
# обновление бота одной командой: /opt/update.sh
cat > /opt/update.sh <<'EOS'
#!/bin/bash
set -e
cd /opt/a && git pull -q && docker build -t bot /opt/a/bot && docker rm -f bot && \
docker run -d --name bot --restart always --env-file /opt/bot.env -v /opt/data:/data -p 127.0.0.1:8080:8080 bot
EOS
chmod +x /opt/update.sh
# автообновление: раз в 2 минуты проверяем новые коммиты в ветке
cat > /etc/cron.d/bot-update <<'EOS'
*/2 * * * * root cd /opt/a && git fetch -q && [ "$(git rev-parse HEAD)" != "$(git rev-parse @{u})" ] && /opt/update.sh >> /var/log/bot-update.log 2>&1
EOS
