"""Связь с контент-заводом: передаёт задачу диспетчеру завода и печатает его ответ.

  python agent/tools/zavod.py "найди тренды про нейросети для экспертов"
  python agent/tools/zavod.py status          что сейчас на заводе
"""
import json
import os
import sys
import urllib.request

URL = os.environ.get("ZAVOD_URL", "").rstrip("/")
TOKEN = os.environ.get("ZAVOD_TOKEN", "")


def call(path, body=None, timeout=900):
    req = urllib.request.Request(URL + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main():
    if not URL or not TOKEN:
        sys.exit("Нет ZAVOD_URL или ZAVOD_TOKEN в переменных сервиса agent: завод недоступен.")
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        sys.exit(__doc__)
    if text == "status":
        d = call("/api/state")
        for r in sorted(d["runs"], key=lambda r: -r["createdAt"])[:10]:
            st = r.get("stage", 0)
            where = "выпущено" if st >= 6 else d["stations"][min(st, 5)]
            busy = f" (сейчас: {d['stations'][r['busy']]})" if r.get("busy") is not None else ""
            print(f"{r['id']} · {r['title']} · {where}{busy}" + (f" · ошибка: {r['error']}" if r.get("error") else ""))
        print("Пульт:", URL)
        return
    print(call("/api/dispatch", {"text": text}).get("answer", ""))


if __name__ == "__main__":
    main()
