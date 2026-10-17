"""Связь с ИИ-офисом из Claude Code.

python agent/office.py team                          команда офиса: id, имя, роль, статус
python agent/office.py task "Имя агента" "задача"    поручить задачу, печатает id задачи
python agent/office.py wait 12 13                    дождаться задач и напечатать отчёты
python agent/office.py tasks                         последние задачи и их статусы
python agent/office.py hire "Имя" "роль" "инструкция" нанять нового агента
"""
import json, os, sys, time, urllib.request, http.cookiejar

URL = os.environ.get('OFFICE_URL', 'https://office-production-833a.up.railway.app').rstrip('/')
jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def call(path, data=None, method=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(URL + path, data=body, method=method or ('POST' if body else 'GET'),
                                 headers={'Content-Type': 'application/json'})
    with op.open(req, timeout=60) as r:
        return json.loads(r.read() or b'null')


def login():
    call('/api/login', {'password': os.environ.get('OFFICE_PASSWORD', '')})


def agents():
    return call('/api/state')['agents']


def find(name):
    for a in agents():
        if str(a['id']) == name or a['name'].lower() == name.lower():
            return a
    for a in agents():
        if name.lower() in a['name'].lower():
            return a
    sys.exit(f'Нет агента «{name}». Команда: python agent/office.py team')


def main(cmd, *args):
    login()
    if cmd == 'team':
        for a in agents():
            print(f"{a['id']}. {a['name']}{' (главный в офисе)' if a['is_main'] else ''} [{a['status']}]: {a['role']}")
    elif cmd == 'task':
        a = find(args[0])
        r = call('/api/tasks', {'agent_id': a['id'], 'title': ' '.join(args[1:]), 'from_main': True})
        print(f"Задача {r['id']} поручена: {a['name']}")
    elif cmd == 'wait':
        ids = {int(x) for x in args}
        deadline = time.time() + 900
        while time.time() < deadline:
            ts = {t['id']: t for t in call('/api/state')['tasks'] if t['id'] in ids}
            if ts and all(t['status'] in ('done', 'error') for t in ts.values()):
                names = {a['id']: a['name'] for a in agents()}
                for t in ts.values():
                    print(f"=== Задача {t['id']} · {names.get(t['agent_id'], '?')} · {t['status']}\n{t['title']}\n--- Отчёт:\n{t['result']}\n")
                return
            time.sleep(5)
        print('Не дождался за 15 минут. Проверь позже: python agent/office.py tasks')
    elif cmd == 'tasks':
        names = {a['id']: a['name'] for a in agents()}
        for t in call('/api/state')['tasks'][:15]:
            print(f"{t['id']}. [{t['status']}] {names.get(t['agent_id'], '?')}: {t['title'][:100]}")
    elif cmd == 'hire':
        r = call('/api/agents', {'name': args[0], 'role': args[1], 'prompt': args[2]})
        print(f"Нанят: {args[0]} (id {r['id']})")
    else:
        print(__doc__)


if __name__ == '__main__':
    main(*(sys.argv[1:] or ['help']))
