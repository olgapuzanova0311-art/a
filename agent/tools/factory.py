"""Завод агентов: главный Claude Code создаёт, запускает и ставит на расписание своих агентов.

Агент завода = субагент Claude Code (.claude/agents/<id>.md) со своей ролью, навыками и инструментами
+ робот в ИИ-офисе + (по желанию) задача по расписанию с отчётом Ольге в Telegram.

python agent/tools/factory.py create <id> --name "Имя" --role "роль одной строкой" --prompt-file путь.md
                                      [--skills навык1,навык2] [--tools Read,Write,Bash,WebSearch,WebFetch] [--model sonnet|opus|haiku|inherit]
python agent/tools/factory.py list                                  все агенты завода и их расписания
python agent/tools/factory.py schedule <id> "<cron>" "задача"       расписание (cron по Москве: "0 9 * * 1-5" = будни в 9:00)
python agent/tools/factory.py unschedule <id> [номер]               снять расписание (все или одно по номеру из list)
python agent/tools/factory.py run <id> "задача"                     запустить сейчас (бот выполнит в фоне и пришлёт отчёт)
python agent/tools/factory.py delete <id>                           уволить агента

Навыки лежат в .claude/skills/<навык>/SKILL.md. Новый навык создай сам: папка + SKILL.md с frontmatter name и description.
"""
import argparse, json, os, re, sys, time
from pathlib import Path

DATA = Path(os.environ.get('DATA', '/data'))
WS = DATA / 'ws'
AGENTS = WS / '.claude' / 'agents'
SKILLS = WS / '.claude' / 'skills'
REG = DATA / 'factory.json'
QUEUE = DATA / 'factory-queue'
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def load():
    try:
        return json.loads(REG.read_text())
    except Exception:
        return {'agents': {}, 'schedules': []}


def save(reg):
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=1))


def slug(s):
    s = re.sub(r'[^a-z0-9-]+', '-', s.lower()).strip('-')
    if not s:
        sys.exit('id агента: латиница, цифры и дефис, например trend-scout')
    return s


def cron_ok(expr):
    parts = expr.split()
    return len(parts) == 5 and all(re.fullmatch(r'[\d*/,\-]+', p) for p in parts)


def office(cmd, *args):
    try:
        import office as o
        o.login()
        if cmd == 'hire':
            name, role, prompt = args
            for a in o.agents():
                if a['name'].lower() == name.lower():
                    return a['id']
            return o.call('/api/agents', {'name': name, 'role': role, 'prompt': prompt})['id']
        if cmd == 'fire':
            o.call(f'/api/agents/{args[0]}', method='DELETE')
    except Exception as e:
        print(f'(офис недоступен: {e})')
    return None


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd')
    ap.add_argument('id', nargs='?')
    ap.add_argument('rest', nargs='*')
    ap.add_argument('--name'); ap.add_argument('--role', default='')
    ap.add_argument('--prompt-file'); ap.add_argument('--skills', default='')
    ap.add_argument('--tools', default='Read,Write,Edit,Bash,Grep,Glob,WebSearch,WebFetch')
    ap.add_argument('--model', default='inherit')
    a = ap.parse_args(argv)
    reg = load()

    if a.cmd == 'create':
        aid = slug(a.id or '')
        if not a.prompt_file or not Path(a.prompt_file).exists():
            sys.exit('Нужен --prompt-file: файл с подробной инструкцией агента (роль, как работает, формат результата)')
        prompt = Path(a.prompt_file).read_text(encoding='utf-8').strip()
        skills = [s.strip() for s in a.skills.split(',') if s.strip()]
        missing = [s for s in skills if not (SKILLS / s / 'SKILL.md').exists()]
        if missing:
            sys.exit(f'Нет навыков: {", ".join(missing)}. Создай .claude/skills/<навык>/SKILL.md или убери из списка.')
        name = a.name or aid
        desc = (a.role or name).replace('\n', ' ')
        body = prompt
        if skills:
            body += '\n\nТвои навыки (прочитай SKILL.md перед работой): ' + ', '.join(f'.claude/skills/{s}/SKILL.md' for s in skills)
        body += ('\n\nПиши по-русски, коротко и по делу. Голос и смыслы Ольги: brand/olga-puzanova-smysly.md. '
                 'Готовые файлы для Ольги клади в outbox/. В конце дай итог: что сделано и что нужно от Ольги.')
        AGENTS.mkdir(parents=True, exist_ok=True)
        (AGENTS / f'{aid}.md').write_text(
            f'---\nname: {aid}\ndescription: {name}. {desc}\ntools: {a.tools}\nmodel: {a.model}\n---\n\n{body}\n', encoding='utf-8')
        oid = office('hire', name, desc[:120], prompt[:7000])
        reg['agents'][aid] = {'name': name, 'role': desc, 'skills': skills, 'tools': a.tools, 'office_id': oid, 'created': time.time()}
        save(reg)
        print(f'Агент {name} ({aid}) создан. Файл .claude/agents/{aid}.md' + (f', в офисе id {oid}' if oid else ''))

    elif a.cmd == 'list':
        if not reg['agents']:
            print('Завод пуст.')
        for aid, x in reg['agents'].items():
            print(f"• {x['name']} ({aid}): {x['role']}" + (f" · навыки: {', '.join(x['skills'])}" if x['skills'] else ''))
        for i, s in enumerate(reg['schedules'], 1):
            print(f"  ⏰ {i}. {s['agent']}: «{s['cron']}» {s['task'][:80]}")

    elif a.cmd == 'schedule':
        aid = slug(a.id or '')
        if aid not in reg['agents']:
            sys.exit(f'Нет агента {aid}. Список: factory.py list')
        if len(a.rest) < 2 or not cron_ok(a.rest[0]):
            sys.exit('Формат: schedule <id> "<мин час день месяц день_недели>" "задача"')
        reg['schedules'].append({'agent': aid, 'cron': a.rest[0], 'task': ' '.join(a.rest[1:]), 'last': ''})
        save(reg)
        print(f'Расписание добавлено: {aid} «{a.rest[0]}» (время московское)')

    elif a.cmd == 'unschedule':
        aid = slug(a.id or '')
        before = len(reg['schedules'])
        if a.rest:
            n = int(a.rest[0]) - 1
            reg['schedules'] = [s for i, s in enumerate(reg['schedules']) if not (i == n and s['agent'] == aid)]
        else:
            reg['schedules'] = [s for s in reg['schedules'] if s['agent'] != aid]
        save(reg)
        print(f'Снято расписаний: {before - len(reg["schedules"])}')

    elif a.cmd == 'run':
        aid = slug(a.id or '')
        if aid not in reg['agents'] or not a.rest:
            sys.exit('Формат: run <id> "задача" (агент должен существовать)')
        QUEUE.mkdir(parents=True, exist_ok=True)
        (QUEUE / f'{time.time():.3f}-{aid}.json').write_text(json.dumps({'agent': aid, 'task': ' '.join(a.rest)}, ensure_ascii=False))
        print(f'Поставлено в очередь: {aid}. Отчёт придёт Ольге в Telegram отдельным сообщением.')

    elif a.cmd == 'delete':
        aid = slug(a.id or '')
        x = reg['agents'].pop(aid, None)
        if not x:
            sys.exit(f'Нет агента {aid}')
        reg['schedules'] = [s for s in reg['schedules'] if s['agent'] != aid]
        (AGENTS / f'{aid}.md').unlink(missing_ok=True)
        if x.get('office_id'):
            office('fire', x['office_id'])
        save(reg)
        print(f'Агент {x["name"]} уволен.')
    else:
        print(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:]) if len(sys.argv) > 1 else print(__doc__)
