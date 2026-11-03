---
name: higgsfield
description: Генерация картинок и видео через API Higgsfield (Soul 2 для реалистичных портретов и фэшн-фото, другие модели из каталога). Использовать, когда Ольга просит сгенерировать фото, обложку, визуал для поста или рилса, портрет в её стиле, или видео через Higgsfield.
---

# Higgsfield API

Ключ лежит в переменной окружения `HF_KEY` в формате `KEY_ID:KEY_SECRET`. Если её нет, скажи Ольге, что нужен ключ из console.higgsfield.ai (раздел API keys).
Расходует кредиты Ольги: перед большими сериями (больше 4 картинок или любое видео) коротко согласуй.

## Как вызывать (cURL)
1. Отправить задачу: `POST https://api.higgsfield.ai/<model_id>` с заголовками `Authorization: Key $HF_KEY` и `Content-Type: application/json`, тело: параметры модели. В ответе `request_id` и `status_url`.
2. Опрашивать `status_url` (тот же заголовок) каждые 3–5 секунд, пока `status` не станет `completed` (или `failed`, `nsfw`, `canceled`).
3. Готовые файлы в `images[].url` (у видео-моделей смотри поле ответа). Скачай в `outbox/`, бот отправит Ольге.

Можно и через Python SDK: `pip install --user higgsfield-client`, `higgsfield_client.subscribe('<model_id>', arguments={...})` (читает `HF_KEY`).

## Soul 2: реалистичные портреты и фэшн
Model ID: `higgsfield-ai/soul/v2/standard`. Параметры:
- `prompt` (обязательный), по-английски даёт лучший результат;
- `aspect_ratio`: `9:16` для рилс и сторис, `4:3`, `3:4`, `1:1`, `16:9`, `2:3`, `3:2`;
- `resolution`: `720p` или `1080p`;
- `batch_size`: 1 или 4;
- `enhance_prompt`: true по умолчанию;
- `style_id` (UUID стиля Soul), `seed` (1–1000000) для повторяемости;
- `custom_reference_id`: Soul ID (обученный образ человека, например самой Ольги), `custom_reference_strength` 0–1.

## Soul ID (образ Ольги)
Создать один раз: `POST https://api.higgsfield.ai/v1/custom-references` с телом `{"name": "...", "model_version": "v2", "input_images": [{"type": "image_url", "image_url": "https://..."}]}` (1–100 фото, ссылки должны открываться без входа). Сохранить `id`, ждать `GET /v1/custom-references/<id>` до `status: completed`. Список: `GET /v1/custom-references/list?page=1&page_size=20`. Найденный id Ольги запиши в agent/MEMORY.md.

## Другие модели
Каталог и параметры любой модели: https://docs.higgsfield.ai/docs/llms.txt и страница модели `https://dash.higgsfield.ai/models/<model_id>/llms.txt`. Прочитай (WebFetch) перед первым вызовом новой модели.

## Стиль Ольги для визуалов
Современные молодые девушки, Instagram-эстетика, никакого странного стока; лучше с её Soul ID. Цвета бренда в монтаже: оранжевый #FF6B1A, синий #2F6BFF, тёмный фон #0A0A0C.
