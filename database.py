import sqlite3
from datetime import datetime

DB_NAME = "alerts.db"


def connect():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        target_price REAL NOT NULL,
        direction TEXT NOT NULL,
        trigger_type TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        rsi_enabled INTEGER DEFAULT 1,
        repeat_mode TEXT DEFAULT 'once',
        status TEXT DEFAULT 'active',
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def add_alert(
    user_id,
    symbol,
    target_price,
    direction,
    trigger_type,
    timeframe,
    rsi_enabled=1,
    repeat_mode="once"
):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO alerts
    (
        user_id,
        symbol,
        target_price,
        direction,
        trigger_type,
        timeframe,
        rsi_enabled,
        repeat_mode,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
        user_id,
        symbol,
        target_price,
        direction,
        trigger_type,
        timeframe,
        rsi_enabled,
        repeat_mode,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def get_user_alerts(user_id):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    SELECT *
    FROM alerts
    WHERE user_id=?
    ORDER BY id DESC
    """,
    (user_id,))

    alerts = cur.fetchall()

    conn.close()

    return alerts


def delete_alert(alert_id, user_id):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    DELETE FROM alerts
    WHERE id=? AND user_id=?
    """,
    (alert_id, user_id))

    conn.commit()
    conn.close()


def toggle_alert(alert_id, user_id):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    UPDATE alerts
    SET status =
    CASE
        WHEN status='active'
        THEN 'paused'
        ELSE 'active'
    END
    WHERE id=? AND user_id=?
    """,
    (alert_id, user_id))

    conn.commit()
    conn.close()
