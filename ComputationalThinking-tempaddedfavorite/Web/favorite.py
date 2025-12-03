import sqlite3
from datetime import datetime

# 🔹 Đồng bộ DB với database.py / app.py
DB_PATH = "Web/Integrate UI and Chatbot/smart_tourism.db"

def add_favorite(user_id, place_id, place_name):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Đảm bảo bảng tồn tại giống database.py
    cur.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            place_id TEXT NOT NULL,
            place_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO favorites (user_id, place_id, place_name, created_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, place_id, place_name, created_at))

    conn.commit()
    conn.close()

    return {"status": "success", "message": "Added to favorites!"}


def get_favorites_by_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Bảo đảm bảng tồn tại
    cur.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            place_id TEXT NOT NULL,
            place_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        SELECT place_id, place_name, created_at
        FROM favorites
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    return rows


def remove_favorite(user_id, place_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Bảo đảm bảng tồn tại
    cur.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            place_id TEXT NOT NULL,
            place_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        DELETE FROM favorites
        WHERE user_id = ? AND place_id = ?
    """, (user_id, place_id))

    conn.commit()
    conn.close()

    return {"status": "success", "message": "Removed"}
