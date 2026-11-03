"""Разовые рассылки с картинкой и именем. Сначала STAGE='test' (только TEST_USERNAMES), после «ок» Ольги STAGE='all'.
Каждое сообщение уходит человеку один раз (отметка в sent / max_sent), поэтому перезапуск бота ничего не дублирует.
"""
import asyncio, html, logging

from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup

log = logging.getLogger('campaign')

KEY = 'dr_replay'
TITLE = 'Повтор эфира в 15:00 и 18:00'
STAGE = 'all'                       # 'test…' → только тест; 'all' → всем пользователям Telegram и MAX; 'done' → рассылка закончена
START = 1793703600                  # 03.11.2026 14:00 МСК: раньше не отправляем, бот ждёт этого времени
UNTIL = 1793709000                  # 03.11.2026 15:30 МСК: позже не отправляем
TEST_USERNAMES = ('olgapuzanovva', 'olgapuzanovvva')
PHOTO = 'mne23.jpg'                 # лежит рядом с ботом; для MAX берём копию с сайта (docs/img)
PHOTO_URL = 'https://agent.olgapuzanovva.ru/img/mne23.jpg'

TEXT = (
    '{hello} если не успел(а) на мой эфир, у меня супер новости 🎉\n\n'
    'Делаю повтор сегодня в 15:00 и в 18:00. Там всё целиком: 23 вывода к 23 годам, '
    'мой ИИ-офис на живом экране и подарки, которые бывают раз в год. '
    'Они сгорают сегодня в 23:23, так что повтор это последний шанс.\n\n'
    'Ссылка на повтор 👉 https://start.bizon365.ru/room/olgapuzanova/mne23'
)
LINK = 'https://start.bizon365.ru/room/olgapuzanova/mne23'
BUTTON = '▶️ Смотреть повтор'


def text_for(first_name):
    name = (first_name or '').strip()
    if name:
        return TEXT.format(hello=f'{html.escape(name)},')
    t = TEXT.format(hello='')
    return t[1].upper() + t[2:]


async def run(M):
    """M: модуль main (q, mark, bot, notify_admins, MX)."""
    if STAGE not in ('all',) and not STAGE.startswith('test'):
        return  # рассылка закончена: новые люди в боте её не получают
    if UNTIL and M.time.time() > UNTIL:
        return  # событие уже прошло
    if START and M.time.time() < START:
        log.info('campaign %s: ждём до %s', KEY, START)
        await asyncio.sleep(START - M.time.time())
    try:
        if STAGE.startswith('test'):
            names = [n.lower() for n in TEST_USERNAMES]
            rows = [r for r in M.q('SELECT * FROM users WHERE blocked=0').fetchall() if (r['username'] or '').lower() in names]
        else:
            rows = M.q('SELECT * FROM users WHERE blocked=0 ORDER BY id').fetchall()
        log.info('campaign %s %s: matched %s users', KEY, STAGE, len(rows))
        mark_key = f'{KEY}:{STAGE}'
        # кто уже получил тест, второй раз то же сообщение не получает
        done = "key = ?" if STAGE.startswith('test') else "(key = ? OR key LIKE '" + KEY + ":test%')"
        todo = [r for r in rows if not M.q(f'SELECT 1 FROM sent WHERE user_id=? AND {done}', r['id'], mark_key).fetchone()]
        if not todo:
            return
        photo = None
        if PHOTO:
            with open(M.os.path.join(M.os.path.dirname(__file__), PHOTO), 'rb') as f:
                photo = BufferedInputFile(f.read(), filename=PHOTO)
        ok = fail = 0
        for r in todo:
            if not M.mark(r['id'], mark_key):
                continue
            try:
                kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BUTTON, url=LINK)]])
                if photo:
                    m = await M.bot.send_photo(r['id'], photo, caption=text_for(r['first_name']), reply_markup=kb)
                    photo = m.photo[-1].file_id  # дальше шлём уже загруженную картинку
                else:
                    await M.bot.send_message(r['id'], text_for(r['first_name']), reply_markup=kb, disable_web_page_preview=True)
                ok += 1
            except Exception as e:
                fail += 1
                if 'blocked' in str(e) or 'deactivated' in str(e) or 'chat not found' in str(e):
                    M.q('UPDATE users SET blocked=1 WHERE id=?', r['id'])
                log.info('campaign %s: %s', r['id'], e)
            await asyncio.sleep(0.05)
        mx = 0
        if STAGE == 'all' and M.MX:
            for r in M.MX.q('SELECT * FROM max_users WHERE blocked=0 ORDER BY id').fetchall():
                if M.MX.q('SELECT 1 FROM max_sent WHERE user_id=? AND key=?', r['id'], mark_key).fetchone():
                    continue
                M.MX.q('INSERT OR IGNORE INTO max_sent(user_id, key) VALUES(?,?)', r['id'], mark_key)
                if await M.MX.send(r['id'], text_for(r['first_name']).replace('{', '{{').replace('}', '}}'),
                                   [[('url', BUTTON, LINK.replace('{', '{{').replace('}', '}}'))]], photo=PHOTO_URL or None):
                    mx += 1
                await asyncio.sleep(0.6)
        what = 'Тест рассылки' if STAGE.startswith('test') else 'Рассылка'
        log.info('campaign %s %s: ok=%s fail=%s max=%s', KEY, STAGE, ok, fail, mx)
        await M.notify_admins(f'📨 {what} «{TITLE}»: доставлено в Telegram {ok}, не доставлено {fail}'
                              + (f', в MAX {mx}' if STAGE == 'all' else '') + '.')
    except Exception:
        log.exception('campaign')
