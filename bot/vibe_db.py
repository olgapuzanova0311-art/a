import os
import sqlite3
import time

DB_PATH = os.environ.get("VIBE_DB_PATH", "/data/vibe.db")

os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
con = sqlite3.connect(DB_PATH, isolation_level=None, check_same_thread=False)
con.row_factory = sqlite3.Row
con.executescript("""
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, name TEXT, username TEXT, src TEXT, reel TEXT,
  started_at REAL, expires_at REAL, second_until REAL DEFAULT 0,
  paid_at REAL, paid_price INTEGER, next_charge REAL, club_active INTEGER DEFAULT 0,
  stopped INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS tags(user_id INTEGER, tag TEXT, ts REAL, PRIMARY KEY(user_id, tag));
CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, user_id INTEGER, key TEXT, due REAL,
  done INTEGER DEFAULT 0, UNIQUE(user_id, key));
CREATE TABLE IF NOT EXISTS events(user_id INTEGER, kind TEXT, key TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS orders(deal TEXT PRIMARY KEY, user_id INTEGER, email TEXT, cost INTEGER, ts REAL);
CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY, chat_id INTEGER, message_id INTEGER, ts REAL);
CREATE TABLE IF NOT EXISTS fwd(chat_id INTEGER, msg INTEGER, user_id INTEGER, PRIMARY KEY(chat_id, msg));
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE INDEX IF NOT EXISTS jobs_due ON jobs(done, due);
CREATE INDEX IF NOT EXISTS events_kind ON events(kind, key);
""")


def q(sql, *a):
    return con.execute(sql, a).fetchall()


def one(sql, *a):
    return con.execute(sql, a).fetchone()


def run(sql, *a):
    return con.execute(sql, a)


def user(uid):
    return one("SELECT * FROM users WHERE id=?", uid)


def tag(uid, t):
    run("INSERT OR IGNORE INTO tags VALUES(?,?,?)", uid, t, time.time())


def untag(uid, t):
    run("DELETE FROM tags WHERE user_id=? AND tag=?", uid, t)


def has(uid, t):
    return one("SELECT 1 FROM tags WHERE user_id=? AND tag=?", uid, t) is not None


def event(uid, kind, key=""):
    run("INSERT INTO events VALUES(?,?,?,?)", uid, kind, key, time.time())


def schedule(uid, key, due):
    run("INSERT INTO jobs(user_id,key,due,done) VALUES(?,?,?,0) "
        "ON CONFLICT(user_id,key) DO UPDATE SET due=excluded.due, done=0", uid, key, due)


def cancel(uid, prefix):
    run("UPDATE jobs SET done=2 WHERE user_id=? AND done=0 AND key LIKE ?", uid, prefix + "%")


def setting(k, default=""):
    r = one("SELECT v FROM settings WHERE k=?", k)
    return r["v"] if r else default


def set_setting(k, v):
    run("INSERT INTO settings VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", k, v)
