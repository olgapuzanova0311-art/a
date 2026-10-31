"""Разовые рассылки с картинкой и именем. Сначала STAGE='test' (только TEST_USERNAMES), после «ок» Ольги STAGE='all'.
Каждое сообщение уходит человеку один раз (отметка в sent / max_sent), поэтому перезапуск бота ничего не дублирует.
"""
import asyncio, html, logging

from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup

log = logging.getLogger('campaign')

KEY = 'dr_team'
TITLE = 'Моя ИИ-команда (размытая)'
STAGE = 'done'                      # 'test…' → только тест; 'all' → всем пользователям Telegram и MAX; 'done' → рассылка закончена
TEST_USERNAMES = ('olgapuzanovva', 'olgapuzanovvva')
PHOTO = 'team.jpg'                  # лежит рядом с ботом; для MAX берём копию с сайта (docs/img)
PHOTO_URL = 'https://agent.olgapuzanovva.ru/img/team.jpg'

TEXT = (
    '{hello} 👀\n\n'
    'Это моя ИИ-команда, пока размытая. Эти сотрудники пишут мои посты, отвечают клиентам, собирают отчёты и ни разу не просили отпуск 😅\n\n'
    '3 ноября, в мой день рождения, в 12:00 открою схему целиком и покажу на живом экране, как всё работает. '
    'Так подробно я это никому не показывала.\n\n'
    '🎟 Билет на эфир: https://olgapuzanova0311-art.github.io/perezagruzka/dr/'
)
LINK = 'https://olgapuzanova0311-art.github.io/perezagruzka/dr/'
BUTTON = '🎟 ЗАБРАТЬ БИЛЕТ 🎟'


def text_for(first_name):
    name = (first_name or '').strip()
    return TEXT.format(hello=f'{html.escape(name)}, смотри, что покажу' if name else 'Смотри, что покажу')


async def run(M):
    """M: модуль main (q, mark, bot, notify_admins, MX)."""
    if STAGE not in ('all',) and not STAGE.startswith('test'):
        return  # рассылка закончена: новые люди в боте её не получают
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
        with open(M.os.path.join(M.os.path.dirname(__file__), PHOTO), 'rb') as f:
            photo = BufferedInputFile(f.read(), filename=PHOTO)
        ok = fail = 0
        for r in todo:
            if not M.mark(r['id'], mark_key):
                continue
            try:
                m = await M.bot.send_photo(r['id'], photo, caption=text_for(r['first_name']), reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text=BUTTON, url=LINK)]]))
                photo = m.photo[-1].file_id  # дальше шлём уже загруженную картинку
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
                                   [[('url', BUTTON, LINK.replace('{', '{{').replace('}', '}}'))]], photo=PHOTO_URL):
                    mx += 1
                await asyncio.sleep(0.6)
        what = 'Тест рассылки' if STAGE.startswith('test') else 'Рассылка'
        log.info('campaign %s %s: ok=%s fail=%s max=%s', KEY, STAGE, ok, fail, mx)
        await M.notify_admins(f'📨 {what} «{TITLE}»: доставлено в Telegram {ok}, не доставлено {fail}'
                              + (f', в MAX {mx}' if STAGE == 'all' else '') + '.')
    except Exception:
        log.exception('campaign')
