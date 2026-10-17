# Claude Code в Telegram: копия рабочего Claude Ольги и главный в ИИ-офисе.
# Собирается из корня репозитория, чтобы внутри были все файлы проекта.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl git ripgrep ca-certificates gnupg ffmpeg fontconfig fonts-dejavu-core build-essential cmake chromium \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update && apt-get install -y --no-install-recommends nodejs gh \
 && npm install -g @anthropic-ai/claude-code @railway/cli \
 && mkdir -p /usr/share/fonts/truetype/brand \
 && for f in montserrat/Montserrat oswald/Oswald manrope/Manrope; do curl -fsSL -o /usr/share/fonts/truetype/brand/$(basename $f).ttf "https://github.com/google/fonts/raw/main/ofl/$f%5Bwght%5D.ttf"; done \
 && fc-cache -f \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY agent/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app/repo
RUN useradd -m -u 1000 agent

ENV PYTHONUNBUFFERED=1 DATA=/data REMOTION_CHROME_EXECUTABLE=/usr/bin/chromium PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
CMD ["sh", "-c", "mkdir -p /data && chown -R agent:agent /data && exec runuser -u agent -- python /app/repo/agent/bot.py"]
