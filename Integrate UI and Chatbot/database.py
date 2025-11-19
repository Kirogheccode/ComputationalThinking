# database.py
import sqlite3
from datetime import datetime

DATABASE = 'Integrate UI and Chatbot\smart_tourism.db'

def get_db_connection():
    """Tạo và trả về kết nối đến cơ sở dữ liệu."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # Cho phép truy cập cột bằng tên
    return conn

def init_db():
    """Khởi tạo cấu trúc bảng trong cơ sở dữ liệu nếu chưa tồn tại."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Bảng người dùng
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Bảng bài đăng món ăn của người dùng
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
    conn.commit()
    conn.close()

def add_user(username, email, password_hash):
    """Thêm người dùng mới vào DB."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                       (username, email, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Username hoặc email đã tồn tại
        return False
    finally:
        conn.close()

def get_user_by_username(username):
    """Lấy thông tin người dùng bằng username."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    """Lấy thông tin người dùng bằng ID."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user

def add_food_post(user_id, food_name, description, image_filename):
    """Thêm một bài đăng món ăn mới vào DB."""
    conn = get_db_connection()
    posted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO food_posts (user_id, food_name, description, image_filename, posted_at) VALUES (?, ?, ?, ?, ?)",
                 (user_id, food_name, description, image_filename, posted_at))
    conn.commit()
    conn.close()

def get_food_posts_by_user(user_id):
    """Lấy tất cả bài đăng món ăn của một người dùng."""
    conn = get_db_connection()
    posts = conn.execute("""
        SELECT fp.*, u.username 
        FROM food_posts fp JOIN users u ON fp.user_id = u.id 
        WHERE fp.user_id = ? 
        ORDER BY posted_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return posts

def get_all_food_posts():
    """Lấy tất cả bài đăng món ăn từ tất cả người dùng (nếu muốn làm trang khám phá chung)."""
    conn = get_db_connection()
    posts = conn.execute("""
        SELECT fp.*, u.username 
        FROM food_posts fp JOIN users u ON fp.user_id = u.id 
        ORDER BY posted_at DESC
    """).fetchall()
    conn.close()
    return posts

if __name__ == '__main__':
    # Khởi tạo DB khi chạy file này trực tiếp lần đầu
    init_db()
    print("Database initialized successfully.")