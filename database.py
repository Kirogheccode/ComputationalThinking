# database.py
import sqlite3
from models import CREATE_HISTORY_TABLE

DB_PATH = "foodapp.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(CREATE_HISTORY_TABLE)
    conn.commit()
    conn.close()

def add_history(user_id, place_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO history (user_id, place_name) VALUES (?, ?)",
        (user_id, place_name)
    )
    conn.commit()
    conn.close()

def get_history(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT place_name, timestamp FROM history WHERE user_id=? ORDER BY id DESC",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows
