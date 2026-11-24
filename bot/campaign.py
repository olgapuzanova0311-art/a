"""Разовые рассылки с картинкой и именем. Сначала STAGE='test' (только TEST_USERNAMES), после «ок» Ольги STAGE='all'.
Каждое сообщение уходит человеку один раз (отметка в sent / max_sent), поэтому перезапуск бота ничего не дублирует.
"""
import asyncio, html, logging

from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup

log = logging.getLogger('campaign')

# Каждая рассылка ждёт своего START и уходит один раз. Несколько штук можно запланировать сразу.
CAMPAIGNS = [
    dict(
        KEY='bf_closed_live',
        TITLE='Закрытый эфир 26.11: ИИ-офис из 10 агентов',
        STAGE='all',                    # 'test…' → только тест; 'all' → всем в Telegram и MAX; 'done' → закончена
        START=0,                        # 0 → сразу после выкладки
        UNTIL=1795543200,               # 24.11.2026 21:00 МСК: в тексте «сегодня с 19:00 до 22:00», позже не отправляем
        PHOTO=None,
        PHOTO_URL=None,
        TEXT=(
            '🔐 ВАМ ДОСТУПЕН ЗАКРЫТЫЙ ЭФИР: СОБИРАЕМ ИИ-ОФИС ИЗ 10 АГЕНТОВ\n\n'
            '26 ноября в 19:00 МСК соберу офис прямо на эфире и покажу, как задача сама проходит через всех агентов без меня. '
            'Живая команда на эти задачи стоила бы около 600 000 ₽ в месяц 🔥\n\n'
            'Шаблон оркестратора, агента, который раздаёт задачи остальным, получат только те, кто будет в прямом эфире. В записи его не будет\n\n'
            '🎁 А ЕЩЁ ВСЕХ, КТО ЗАРЕГИСТРИРУЕТСЯ, ЖДЁТ НАБОР ПОДАРКОВ:\n\n'
            '🤖 «ИИ-ассистент по задачам»\nСам собирает задачи из чатов, календаря и зумов и напоминает в боте\n'
            '🧰 «Набор селлера»\nЛучшие ИИ-инструменты для работы на маркетплейсах\n'
            '🎬 «50 форматов рилс с хуками»\nГотовые идеи роликов, которые цепляют с первых секунд\n'
            '💳 «Грант на 3 000 ₽»\nНа мои продукты 2027 года\n\n'
            '🥚 А сегодня с 19:00 до 22:00 на сайте будет золотое яйцо: чек-лист на 30 идей агентов под ваш бизнес\n\n'
            'Забирайте всё по клику 👇'
        ),
        NAMED=False,
        LINK='https://bf.olgapuzanovva.ru/',
        BUTTON='✅ ЗАБРАТЬ ПОДАРКИ ✅',
        REPEAT=3,                       # три одинаковые кнопки друг под другом
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
                kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BUTTON, url=LINK)] for _ in range(c.get('REPEAT', 1))])
                text = text_for(c, r['first_name'])
                if photo and len(text) > 1024:
                    # подпись к фото в Telegram не длиннее 1024 символов: картинку шлём отдельно, текст с кнопкой следом
                    m = await M.bot.send_photo(r['id'], photo)
                    photo = m.photo[-1].file_id
                    await M.bot.send_message(r['id'], text, reply_markup=kb, disable_web_page_preview=True)
                elif photo:
                    m = await M.bot.send_photo(r['id'], photo, caption=text, reply_markup=kb)
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
                                   [[('url', BUTTON, LINK.replace('{', '{{').replace('}', '}}'))]] * c.get('REPEAT', 1), photo=PHOTO_URL or None):
                    mx += 1
                await asyncio.sleep(0.6)
        what = 'Тест рассылки' if STAGE.startswith('test') else 'Рассылка'
        log.info('campaign %s %s: ok=%s fail=%s max=%s', KEY, STAGE, ok, fail, mx)
        await M.notify_admins(f'📨 {what} «{TITLE}»: доставлено в Telegram {ok}, не доставлено {fail}'
                              + (f', в MAX {mx}' if STAGE == 'all' else '') + '.')
    except Exception:
        log.exception('campaign')
