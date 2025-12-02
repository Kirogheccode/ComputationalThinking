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

    # Bảng OTP (Lưu mã OTP và thời gian hết hạn)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_otp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            otp_code TEXT NOT NULL,
            expired_at TEXT NOT NULL
        )
    """)

    # Bảng bài đăng (Giữ nguyên)
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

# --- User Functions ---
def add_user(username, email, password_hash):
    """Thêm người dùng đã xác thực vào DB."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # verified = 1 vì chỉ add khi đã verify xong
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

# --- OTP Functions ---
def save_otp(email, otp_code):
    """Lưu OTP mới, xóa OTP cũ nếu có."""
    conn = get_db_connection()
    # Xóa OTP cũ của email này
    conn.execute("DELETE FROM email_otp WHERE email = ?", (email,))
    
    # OTP hết hạn sau 5 phút
    expired_at = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    
    conn.execute("INSERT INTO email_otp (email, otp_code, expired_at) VALUES (?, ?, ?)",
                 (email, otp_code, expired_at))
    conn.commit()
    conn.close()

def verify_otp_code(email, otp_input):
    """Kiểm tra OTP có đúng và còn hạn không."""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM email_otp WHERE email = ?", (email,)).fetchone()
    conn.close()

    if row:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if row['otp_code'] == otp_input and row['expired_at'] > now:
            # OTP đúng và còn hạn -> Xóa OTP để không dùng lại được
            conn = get_db_connection()
            conn.execute("DELETE FROM email_otp WHERE email = ?", (email,))
            conn.commit()
            conn.close()
            return True
    return False

# --- Food Post Functions (Giữ nguyên) ---
def add_food_post(user_id, food_name, description, image_filename):
    conn = get_db_connection()
    posted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO food_posts (user_id, food_name, description, image_filename, posted_at) VALUES (?, ?, ?, ?, ?)",
                 (user_id, food_name, description, image_filename, posted_at))
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

def get_or_create_oauth_user(username, email):
    """
    Tìm user theo email. Nếu chưa có thì tạo mới.
    Dùng cho Google/Facebook login.
    """
    conn = get_db_connection()
    try:
        # 1. Kiểm tra email
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            return user # User đã tồn tại, trả về thông tin
        
        # 2. Nếu chưa có, tạo user mới
        # Tạo password ngẫu nhiên (vì user này dùng OAuth)
        dummy_password = str(uuid.uuid4())
        hashed_password = generate_password_hash(dummy_password)
        
        # Xử lý trùng Username: Nếu username trùng, thêm số ngẫu nhiên
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            username = f"{username}_{random.randint(1000, 9999)}"

        # verified = 1 vì Google/FB đã xác thực email
        cursor.execute("INSERT INTO users (username, email, password, verified) VALUES (?, ?, ?, 1)",
                       (username, email, hashed_password))
        conn.commit()
        
        # Lấy lại user vừa tạo
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        new_user = cursor.fetchone()
        return new_user

    except Exception as e:
        print(f"Lỗi DB OAuth: {e}")
        return None
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized with OTP support.")

    