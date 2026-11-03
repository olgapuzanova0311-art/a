---
name: montage
description: Монтаж видео для Ольги (рилс, шортс, нарезки с эфиров): вертикальный формат 9:16, вырезание пауз, субтитры по речи, музыка, склейка, обложка. Использовать, когда Ольга присылает видео или просит смонтировать, нарезать, сделать рилс, добавить субтитры, музыку или обложку.
---

# Монтаж на ffmpeg

Входящие файлы лежат в `inbox/`. Готовое клади в `outbox/`: всё, что появится там за время задачи, бот сам отправит Ольге в Telegram (видео до 50 МБ, больше: сожми или порежь на части). Рабочие файлы держи в `work/`.

## Порядок работы
1. Посмотри исходник: `ffprobe -v error -show_entries format=duration:stream=width,height,codec_type -of json inbox/файл`.
2. Если нужен смысл, а не просто техника, расшифруй: `python agent/tools/subs.py text inbox/файл`. По тексту выбери сильные куски (хук в первые 3 секунды, одна мысль, призыв в конце). Голос и смыслы Ольги: `brand/olga-puzanova-smysly.md`.
3. Собери ролик рецептами ниже. Проверь результат: длительность, что звук есть, кадр из середины (`ffmpeg -ss 5 -i out.mp4 -frames:v 1 work/check.jpg` и посмотри картинку).
4. Положи в `outbox/` с понятным именем и напиши Ольге коротко, что сделано и что можно поправить.

## Рецепты
Вертикаль 9:16 из горизонтального (кадр по центру):
`ffmpeg -y -i in.mp4 -vf "crop=ih*9/16:ih,scale=1080:1920" -c:a aac -b:a 160k -c:v libx264 -preset veryfast -crf 21 work/v.mp4`
Вертикаль с размытым фоном (видео целиком):
`ffmpeg -y -i in.mp4 -filter_complex "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30[bg];[0:v]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2" -c:a copy -c:v libx264 -preset veryfast -crf 21 work/v.mp4`
Отрезок: `ffmpeg -y -ss 00:01:05 -to 00:01:40 -i in.mp4 -c:v libx264 -preset veryfast -crf 21 -c:a aac work/cut.mp4`
Вырезать паузы: `python agent/tools/subs.py silences in.mp4 --gap 0.6` даёт список [начало, конец]; режь куски и склеивай через concat (`file 'part1.mp4'` в list.txt, `ffmpeg -f concat -safe 0 -i list.txt -c copy work/joined.mp4`), куски перекодируй одинаково.
Субтитры для рилс (крупные, подсветка слова): `python agent/tools/subs.py ass work/v.mp4 work/s.ass --words 3`, затем `ffmpeg -y -i work/v.mp4 -vf "ass=work/s.ass:fontsdir=/usr/share/fonts" -c:a copy -c:v libx264 -preset veryfast -crf 21 work/subs.mp4`. Шрифты Oswald, Manrope и Montserrat установлены. Субтитры делай по готовому (уже обрезанному) видео.
Обычные субтитры: `python agent/tools/subs.py srt in.mp4 work/s.srt`, затем `-vf "subtitles=work/s.srt:force_style='FontName=Montserrat,FontSize=14,Outline=2'"`.
Музыка под голос (тихо, с приглушением): `ffmpeg -y -i v.mp4 -stream_loop -1 -i music.mp3 -filter_complex "[1:a]volume=0.12[m];[0:a][m]amix=inputs=2:duration=first[a]" -map 0:v -map "[a]" -c:v copy -c:a aac out.mp4`. Музыку бери только присланную Ольгой (inbox/), чужие треки не скачивай.
Текст-хук сверху первые 3 секунды: `drawtext=fontfile=/usr/share/fonts/truetype/brand/Oswald.ttf:text='ТЕКСТ':fontsize=78:fontcolor=white:box=1:boxcolor=0xFF6B1A@0.95:boxborderw=24:x=(w-tw)/2:y=260:enable='lt(t,3)'` (апострофы и двоеточия в тексте экранируй).
Обложка: `ffmpeg -ss 2 -i out.mp4 -frames:v 1 outbox/cover.jpg`, при необходимости добавь drawtext.
Сжать до 50 МБ: подбери `-crf 26..30` или `-b:v` под длительность.

## Стиль Ольги (как в reel-montage)
Фон #0A0A0C, акцент оранжевый #FF6B1A, второй синий #2F6BFF. Заголовки Oswald капсом, текст Manrope, субтитры по словам с оранжевым текущим словом. Безопасные зоны: 170 px сверху и снизу, 80 px по бокам. Рилс 20–45 секунд, хук в первые 3 секунды, одна мысль, призыв в конце (кодовое слово или «ссылка в профиле»). Без капслока в тексте поста, в субтитрах капс допустим.
