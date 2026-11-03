"""Разовые рассылки с картинкой и именем. Сначала STAGE='test' (только TEST_USERNAMES), после «ок» Ольги STAGE='all'.
Каждое сообщение уходит человеку один раз (отметка в sent / max_sent), поэтому перезапуск бота ничего не дублирует.
"""
import asyncio, html, logging

from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup

log = logging.getLogger('campaign')

# Каждая рассылка ждёт своего START и уходит один раз. Несколько штук можно запланировать сразу.
CAMPAIGNS = [
    dict(
        KEY='dr_last',
        TITLE='Последний показ в 18:00',
        STAGE='all',                    # 'test…' → только тест; 'all' → всем в Telegram и MAX; 'done' → закончена
        START=1793712900,               # 03.11.2026 16:35 МСК
        UNTIL=1793718000,               # 03.11.2026 18:00 МСК: позже не отправляем
        PHOTO='mne23.jpg',              # лежит рядом с ботом; для MAX берём копию с сайта (docs/img)
        PHOTO_URL='https://agent.olgapuzanovva.ru/img/mne23.jpg',
        TEXT=(
            '🎂 Сегодня у Ольги день рождения, и в 18:00 по Москве последний показ праздничного эфира «Мне 23»\n\n'
            'Ольга делится 23 выводами, которые поняла к своим 23 годам, и показывает изнутри свой ИИ-офис '
            'и контент-завод. А в конце открывает тайный лот для тех, кто досидит до конца.\n\n'
            'Подключайтесь в 18:00:\n'
            'https://start.bizon365.ru/room/102108/mne23'
        ),
        NAMED=False,
        LINK='https://start.bizon365.ru/room/102108/mne23',
        BUTTON='▶️ Подключиться в 18:00',
    ),
    dict(
        KEY='dr_replay2',
        TITLE='Начинаем последний повтор',
        STAGE='all',
        START=1793717700,               # 03.11.2026 17:55 МСК
        UNTIL=1793719800,               # 03.11.2026 18:30 МСК: позже не отправляем
        PHOTO='mne23.jpg',
        PHOTO_URL='https://agent.olgapuzanovva.ru/img/mne23.jpg',
        TEXT=('Начинаем последний повтор эфира «Мне 23» 🔥\n\n'
              'Больше показов не будет. Подключайся 👇\n'
              'https://start.bizon365.ru/room/olgapuzanova/mne23'),
        NAMED=False,
        LINK='https://start.bizon365.ru/room/olgapuzanova/mne23',
        BUTTON='▶️ Подключиться',
    ),
    dict(
        KEY='dr_lots',
        TITLE='Подарки уже разбирают',
        STAGE='all',
        START=1793721600,               # 03.11.2026 19:00 МСК
        UNTIL=1793737380,               # 03.11.2026 23:23 МСК: лоты сгорают
        PHOTO='mne23.jpg',
        PHOTO_URL='https://agent.olgapuzanovva.ru/img/mne23.jpg',
        TEXT=(
            '{hello}одарки дня рождения уже разбирают 🔥\n\n'
            'Царь лот: весь 2027 год всех моих курсов с кураторами за 73 323 ₽ или 6 111 ₽ в месяц, '
            'мест всего 23. И ещё 7 лотов, от тайной коробки за 923 ₽ до года работы со мной.\n\n'
            'К любому лоту бонус с колеса и инструкция, как собрать свой ИИ-офис. Всё действует до 23:23 👇\n'
            'https://olgapuzanova0311-art.github.io/perezagruzka/dr/lots-23x7/'
        ),
        NAMED=True,                     # «Имя, подарки…» / без имени «Подарки…»
        LINK='https://olgapuzanova0311-art.github.io/perezagruzka/dr/lots-23x7/',
        BUTTON='🎁 Забрать подарок',
    ),
    dict(
        KEY='dr_hour',
        TITLE='Остался час',
        STAGE='all',
        START=1793733780,               # 03.11.2026 22:23 МСК
        UNTIL=1793737380,               # 03.11.2026 23:23 МСК: лоты сгорают
        PHOTO='mne23.jpg',
        PHOTO_URL='https://agent.olgapuzanovva.ru/img/mne23.jpg',
        TEXT=('Остался час ⏰ В 23:23 лоты дня рождения сгорят до следующего года 👇 '
              'https://olgapuzanova0311-art.github.io/perezagruzka/dr/lots-23x7/'),
        NAMED=False,
        LINK='https://olgapuzanova0311-art.github.io/perezagruzka/dr/lots-23x7/',
        BUTTON='🎁 Забрать подарок',
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
