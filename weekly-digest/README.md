# Недельная сводка задач

Раз в неделю (по пятницам в 17:52 по Москве) агент:

1. читает твои рабочие чаты и личку в **Telegram**, задачи и чаты в **YouGile**, нужные **Google Таблицы** и записи встреч в **Zoom**;
2. с помощью Claude вытаскивает оттуда всё, что кто-то обещал или кому-то поручили (включая «пришлю завтра» и «посмотрю и вернусь»);
3. убирает дубли и отмечает, что уже заведено в YouGile;
4. присылает тебе в Telegram (в «Избранное») сводку из четырёх разделов:
   **🔥 Мне сделать · ⏳ Жду от других · ❓ Обсудили, но никто не взял · ✅ Сделано**, с ответственными, сроками и ссылками на сообщения.

По желанию задачи можно ещё дописывать в Google Таблицу-архив и сразу заводить в YouGile.

---

## Что понадобится (один раз, ~30–40 минут)

Подключать всё сразу не обязательно: любой источник выключается в конфиге (`enabled: false`).

### 1. Ключ Claude
console.anthropic.com → Settings → API keys → Create key. Это `ANTHROPIC_API_KEY`.
Сводка за неделю обычно стоит от нескольких центов до пары долларов, в зависимости от объёма переписки.

### 2. Telegram
1. Зайди на https://my.telegram.org → **API development tools** → создай приложение (название любое).
   Получишь `api_id` и `api_hash` → это `TG_API_ID` и `TG_API_HASH`.
2. На своём компьютере (нужен Python 3.10+):
   ```bash
   cd weekly-digest
   pip install -r requirements.txt
   python scripts/telegram_login.py
   ```
   Введи телефон и код из Telegram. Скрипт напечатает длинную строку — это `TG_SESSION`.

> ⚠️ `TG_SESSION` даёт полный доступ к твоему аккаунту Telegram. Не пересылай её и не вставляй в файлы репозитория, только в секреты.
> Если что-то пойдёт не так, отключить её можно в Telegram: Настройки → Устройства.

Почему не бот: бот не видит твою личку и чаты, куда его не добавили. Агент читает от твоего имени, но **только читает** и пишет сводку тебе в «Избранное».

### 3. YouGile — ключ API
В терминале (подставь свою почту и пароль от YouGile):
```bash
# узнать id компании
curl -s -X POST https://ru.yougile.com/api-v2/auth/companies \
  -H 'Content-Type: application/json' \
  -d '{"login":"you@mail.ru","password":"ПАРОЛЬ"}'

# создать ключ (companyId из ответа выше)
curl -s -X POST https://ru.yougile.com/api-v2/auth/keys \
  -H 'Content-Type: application/json' \
  -d '{"login":"you@mail.ru","password":"ПАРОЛЬ","companyId":"ID_КОМПАНИИ"}'
```
Ответ `{"key": "..."}` — это `YOUGILE_API_KEY`.

### 4. Google Таблицы
1. https://console.cloud.google.com → создай проект → включи **Google Sheets API**.
2. IAM → **Service Accounts** → Create → в созданном аккаунте Keys → Add key → JSON. Скачается файл.
3. Содержимое файла целиком (одной строкой) — это `GOOGLE_SERVICE_ACCOUNT_JSON`.
4. В каждой нужной таблице нажми «Поделиться» и добавь email сервисного аккаунта (вида `...@...iam.gserviceaccount.com`) как читателя
   (или редактора — для таблицы-архива, куда агент будет дописывать задачи).

### 5. Zoom
Чтобы были транскрипты, в Zoom должны быть включены **облачная запись** и **Audio transcript**
(Settings → Recording → Cloud recording → Create audio transcript). Это платный тариф Zoom.
Если есть **AI Companion** — агент возьмёт и его саммари встречи.

1. https://marketplace.zoom.us → Develop → Build App → **Server-to-Server OAuth**.
2. Scopes: `cloud_recording:read:list_user_recordings:admin`, `cloud_recording:read:recording:admin`,
   `meeting:read:summary:admin` (последний — для саммари AI Companion).
3. Activate. Со страницы App Credentials возьми `Account ID`, `Client ID`, `Client Secret` → `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`.

Нет облачной записи? Включи раздел `notes` в конфиге и складывай туда транскрипты/заметки встреч (.txt, .md, .vtt) — агент прочитает их тоже.

---

## Настройка

```bash
cd weekly-digest
cp config.example.yaml config.yaml   # тут: какие чаты, таблицы, куда слать
cp .env.example .env                 # тут: ключи из шагов выше
```

В `config.yaml` главное:
- `me` — как тебя зовут в чатах;
- `telegram.chats` — список рабочих чатов **или** `all_active: true`, чтобы брать все чаты с активностью за неделю (ненужное — в `exclude`).

## Проверить у себя

```bash
python -m digest.main --collect-only   # только скачать данные и проверить доступы (без Claude)
python -m digest.main --dry-run        # собрать сводку и показать на экране, никуда не отправлять
python -m digest.main                  # по-настоящему: прислать в Telegram
python -m digest.main --days 14        # за две недели
```
Сводки также сохраняются в `output/` (Markdown + JSON).

## Запуск по расписанию (без своего сервера)

Расписание уже настроено в `.github/workflows/weekly-digest.yml` — GitHub сам запускает агента по пятницам.

> ⚠️ **Репозиторий должен быть приватным.** Логи запусков видны всем, у кого есть доступ к репозиторию.

1. GitHub → репозиторий → **Settings → Secrets and variables → Actions → New repository secret**.
2. Добавь секреты с теми же именами, что в `.env`:
   `ANTHROPIC_API_KEY`, `TG_API_ID`, `TG_API_HASH`, `TG_SESSION`, `YOUGILE_API_KEY`,
   `GOOGLE_SERVICE_ACCOUNT_JSON`, `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`.
3. И ещё один секрет `DIGEST_CONFIG` — туда целиком вставь содержимое своего `config.yaml`.
4. Проверка: вкладка **Actions → Недельная сводка задач → Run workflow**. Через пару минут сводка придёт в «Избранное».

Поменять день/время — строка `cron` в workflow (время в UTC, Москва = UTC+3).

## Что важно знать

- Переписки отправляются в Claude API (Anthropic) для разбора. По умолчанию данные API не используются для обучения моделей.
- Если какой-то источник не открылся (истёк ключ, нет доступа к таблице), сводка всё равно придёт, а внизу будет пометка, что именно не прочиталось.
- Таблицы читаются целиком в текущем состоянии (в Google Sheets нет истории по строкам), поэтому в `note` полезно подсказать, какие колонки что значат.
- Голосовые и кружки пока не расшифровываются — в сводке они видны как «[голосовое]».

## Как устроено

```
digest/
  sources/telegram.py  — чтение чатов (Telethon) и отправка сводки
  sources/yougile.py   — задачи, чаты задач, групповые чаты; создание задач
  sources/sheets.py    — чтение таблиц, запись архива
  sources/zoom.py      — транскрипты записей и саммари AI Companion
  extract.py           — Claude: задачи из каждого источника → общая сводка без дублей
  render.py            — оформление для Telegram и Markdown
  main.py              — запуск
```
