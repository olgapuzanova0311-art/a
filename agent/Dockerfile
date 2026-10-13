# Claude Code в Telegram: копия рабочего Claude Ольги и главный в ИИ-офисе.
# Собирается из корня репозитория, чтобы внутри были все файлы проекта.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl git ripgrep ca-certificates gnupg \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && npm install -g @anthropic-ai/claude-code \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY agent/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app/repo
RUN useradd -m -u 1000 agent

ENV PYTHONUNBUFFERED=1 DATA=/data
CMD ["sh", "-c", "mkdir -p /data && chown -R agent:agent /data && exec runuser -u agent -- python /app/repo/agent/bot.py"]
