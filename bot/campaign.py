"""Разовые рассылки с картинкой и именем. Сначала STAGE='test' (только TEST_USERNAMES), после «ок» Ольги STAGE='all'.
Каждое сообщение уходит человеку один раз (отметка в sent / max_sent), поэтому перезапуск бота ничего не дублирует.
"""
import asyncio, html, logging

from aiogram.types import BufferedInputFile

log = logging.getLogger('campaign')

KEY = 'dr_nov3'
STAGE = 'test'                      # 'test' → только тест; 'all' → всем пользователям Telegram и MAX
TEST_USERNAMES = ('olgapuzanovva', 'olgapuzanovvva')
PHOTO = 'dr3.jpg'                   # лежит рядом с ботом; для MAX берём копию с сайта (docs/img)
PHOTO_URL = 'https://agent.olgapuzanovva.ru/img/dr3.jpg'

TEXT = (
    '{hello} Это Оля, и это приглашение я отправляю один раз в год 💌\n\n'
    '3 ноября у меня день рождения. В этом году я решила отметить его с теми, кто учится и растёт вместе со мной, '
    'поэтому в 12:00 по Москве выйду в большой праздничный эфир. Там будет всё, о чём меня обычно спрашивают в личке, '
    'только честнее: итоги года с ошибками и выводами, мой план на 2027 и ИИ-сотрудники, которые работают у меня каждый день, на живом экране.\n\n'
    'А в конце будет сюрприз, который я делаю раз в год. Только для тех, кто в эфире, в записи его не будет 🤫\n\n'
    'Забери секретный билет, пока они есть 👇\n'
    'https://olgapuzanova0311-art.github.io/perezagruzka/dr/\n'
    'У кого он будет, получат на эфире отдельный подарок 🎁'
)


def text_for(first_name):
    name = (first_name or '').strip()
    return TEXT.format(hello=f'{html.escape(name)}, привет!' if name else 'Привет!')


async def run(M):
    """M: модуль main (q, mark, bot, notify_admins, MX)."""
    try:
        if STAGE == 'test':
            names = [n.lower() for n in TEST_USERNAMES]
            rows = [r for r in M.q('SELECT * FROM users WHERE blocked=0').fetchall() if (r['username'] or '').lower() in names]
        else:
            rows = M.q('SELECT * FROM users WHERE blocked=0 ORDER BY id').fetchall()
        log.info('campaign %s %s: matched %s users', KEY, STAGE, len(rows))
        mark_key = f'{KEY}:{STAGE}'
        # кто уже получил тест, второй раз то же сообщение не получает
        todo = [r for r in rows if not M.q('SELECT 1 FROM sent WHERE user_id=? AND key IN (?, ?)', r['id'], mark_key, f'{KEY}:test').fetchone()]
        if not todo:
            return
        with open(M.os.path.join(M.os.path.dirname(__file__), PHOTO), 'rb') as f:
            photo = BufferedInputFile(f.read(), filename=PHOTO)
        ok = fail = 0
        for r in todo:
            if not M.mark(r['id'], mark_key):
                continue
            try:
                m = await M.bot.send_photo(r['id'], photo, caption=text_for(r['first_name']))
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
                if await M.MX.send(r['id'], text_for(r['first_name']).replace('{', '{{').replace('}', '}}'), photo=PHOTO_URL):
                    mx += 1
                await asyncio.sleep(0.6)
        what = 'Тест рассылки' if STAGE == 'test' else 'Рассылка'
        log.info('campaign %s %s: ok=%s fail=%s max=%s', KEY, STAGE, ok, fail, mx)
        await M.notify_admins(f'📨 {what} «День рождения 3 ноября»: доставлено в Telegram {ok}, не доставлено {fail}'
                              + (f', в MAX {mx}' if STAGE == 'all' else '') + '.')
    except Exception:
        log.exception('campaign')
