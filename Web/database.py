# database.py
import sqlite3
from datetime import datetime, timedelta
import uuid 
import random
from werkzeug.security import generate_password_hash

DATABASE = 'Web/Integrate UI and Chatbot/smart_tourism.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Bảng người dùng (Thêm cột verified)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            verified INTEGER DEFAULT 0
        )
    """)

    # Bảng OTP
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_otp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            otp_code TEXT NOT NULL,
            expired_at TEXT NOT NULL
        )
    """)

    # Bảng bài đăng
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            food_name TEXT NOT NULL,
            description TEXT NOT NULL,
            image_filename TEXT,
            posted_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Bảng lưu nhà hàng yêu thích (có chống trùng)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            place_id TEXT NOT NULL,
            place_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (user_id, place_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# ======================================
# USER FUNCTIONS
# ======================================

def add_user(username, email, password_hash):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, password, verified) VALUES (?, ?, ?, 1)",
                       (username, email, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_username(username):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return user

def get_user_by_email(email):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


# ======================================
# OTP FUNCTIONS
# ======================================

def save_otp(email, otp_code):
    conn = get_db_connection()
    
    conn.execute("DELETE FROM email_otp WHERE email = ?", (email,))
    
    expired_at = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    
    conn.execute("INSERT INTO email_otp (email, otp_code, expired_at) VALUES (?, ?, ?)",
                 (email, otp_code, expired_at))
    conn.commit()
    conn.close()


def verify_otp_code(email, otp_input):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM email_otp WHERE email = ?", (email,)).fetchone()
    conn.close()

    if row:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if row['otp_code'] == otp_input and row['expired_at'] > now:
            conn = get_db_connection()
            conn.execute("DELETE FROM email_otp WHERE email = ?", (email,))
            conn.commit()
            conn.close()
            return True
    return False


# ======================================
# FOOD POST FUNCTIONS
# ======================================

def add_food_post(user_id, food_name, description, image_filename):
    conn = get_db_connection()
    posted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""
        INSERT INTO food_posts (user_id, food_name, description, image_filename, posted_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, food_name, description, image_filename, posted_at))

    conn.commit()
    conn.close()


def get_food_posts_by_user(user_id):
    conn = get_db_connection()
    posts = conn.execute("""
        SELECT fp.*, u.username 
        FROM food_posts fp JOIN users u ON fp.user_id = u.id 
        WHERE fp.user_id = ? 
        ORDER BY posted_at DESC
    """, (user_id,)).fetchall()

    conn.close()
    return posts


# ======================================
# OAUTH USER
# ======================================

def get_or_create_oauth_user(username, email):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            return user
        
        dummy_password = str(uuid.uuid4())
        hashed_password = generate_password_hash(dummy_password)
        
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            username = f"{username}_{random.randint(1000, 9999)}"

        cursor.execute("INSERT INTO users (username, email, password, verified) VALUES (?, ?, ?, 1)",
                       (username, email, hashed_password))
        conn.commit()
        
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        new_user = cursor.fetchone()
        return new_user

    except Exception as e:
        print(f"Lỗi DB OAuth: {e}")
        return None

    finally:
        conn.close()



# ======================================
# FAVORITE FUNCTIONS
# ======================================

def add_favorite(user_id, place_id, place_name):
    conn = get_db_connection()
    cursor = conn.cursor()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cursor.execute("""
            INSERT INTO favorites (user_id, place_id, place_name, created_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, place_id, place_name, created_at))
    except sqlite3.IntegrityError:
        # Nếu trùng (user_id + place_id), bỏ qua
        pass

    conn.commit()
    conn.close()


def get_favorites_by_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    rows = cursor.execute("""
        SELECT place_id, place_name, created_at
        FROM favorites
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,)).fetchall()

    conn.close()

    # Chuyển sqlite Row -> dict để jsonify được
    return [
        {
            "place_id": row["place_id"],
            "place_name": row["place_name"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]


def remove_favorite(user_id, place_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM favorites 
        WHERE user_id = ? AND place_id = ?
    """, (user_id, place_id))

    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    print("Database initialized with OTP + Favorites support.")
