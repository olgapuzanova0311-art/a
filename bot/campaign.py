"""Разовые рассылки с картинкой и именем. Сначала STAGE='test' (только TEST_USERNAMES), после «ок» Ольги STAGE='all'.
Каждое сообщение уходит человеку один раз (отметка в sent / max_sent), поэтому перезапуск бота ничего не дублирует.
"""
import asyncio, html, logging

from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup

log = logging.getLogger('campaign')

# Каждая рассылка ждёт своего START и уходит один раз. Несколько штук можно запланировать сразу.
CAMPAIGNS = [
    dict(
        KEY='bf_3eggs',
        TITLE='3 яйца: финальный эфир 26.11',
        STAGE='all',                    # 'test…' → только тест; 'all' → всем в Telegram и MAX; 'done' → закончена
        START=0,                        # 0 → сразу после выкладки
        UNTIL=1795708800,               # 26.11.2026 19:00 МСК: после начала эфира не отправляем
        PHOTO='yaica.jpg',              # лежит рядом с ботом; для MAX берём копию с сайта (docs/img)
        PHOTO_URL='https://agent.olgapuzanovva.ru/img/yaica.jpg',
        TEXT=(
            'ПРИВЕТ, ЭТО ОЛЬГА! У МЕНЯ ДЛЯ ТЕБЯ 3 ЯЙЦА 🍳\n\n'
            'Я запускаю финальный эфир моего челленджа "Черная ИИшница", где собираю 10 ии-агентов на 600.000 руб, и там есть яйца\n\n'
            'Каждое разбиваете одним нажатием, а внутри тебя ждет подарок:\n\n'
            '🎁 1. набор лучших ии-инструментов для селлера\n'
            '🎁 2. 50 форматов топовых рилс с хуками\n'
            '🎁 3. грант от меня на 3 000 ₽ на продукты 2027 года\n\n'
            '26.11 в 19:00 на этом же сайте соберу ИИ-офис из 10 агентов.'
        ),
        NAMED=False,
        LINK='https://bf.olgapuzanovva.ru',
        BUTTON='РАЗБИТЬ ЯЙЦА',
    ),
]
TEST_USERNAMES = ('olgapuzanovva', 'olgapuzanovvva')


def text_for(c, first_name):
    if not c['NAMED']:
        return c['TEXT']
    name = (first_name or '').strip()
    return c['TEXT'].format(hello=f'{html.escape(name)}, п' if name else 'П')


async def run(M):
    """M: модуль main (q, mark, bot, notify_admins, MX)."""
    await asyncio.gather(*(run_one(M, c) for c in CAMPAIGNS))


async def run_one(M, c):
    KEY, TITLE, STAGE, START, UNTIL = c['KEY'], c['TITLE'], c['STAGE'], c['START'], c['UNTIL']
    PHOTO, PHOTO_URL, LINK, BUTTON = c['PHOTO'], c['PHOTO_URL'], c['LINK'], c['BUTTON']
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
                    m = await M.bot.send_photo(r['id'], photo, caption=text_for(c, r['first_name']), reply_markup=kb)
                    photo = m.photo[-1].file_id  # дальше шлём уже загруженную картинку
                else:
                    await M.bot.send_message(r['id'], text_for(c, r['first_name']), reply_markup=kb, disable_web_page_preview=True)
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
                if await M.MX.send(r['id'], text_for(c, r['first_name']).replace('{', '{{').replace('}', '}}'),
                                   [[('url', BUTTON, LINK.replace('{', '{{').replace('}', '}}'))]], photo=PHOTO_URL or None):
                    mx += 1
                await asyncio.sleep(0.6)
        what = 'Тест рассылки' if STAGE.startswith('test') else 'Рассылка'
        log.info('campaign %s %s: ok=%s fail=%s max=%s', KEY, STAGE, ok, fail, mx)
        await M.notify_admins(f'📨 {what} «{TITLE}»: доставлено в Telegram {ok}, не доставлено {fail}'
                              + (f', в MAX {mx}' if STAGE == 'all' else '') + '.')
    except Exception:
        log.exception('campaign')
