# database.py
import sqlite3
from datetime import datetime, timedelta
import uuid 
import random
from flask import session
from werkzeug.security import generate_password_hash

DATABASE = 'data/smart_tourism.db'

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
            verified INTEGER DEFAULT 0,
            avatar TEXT DEFAULT 'default.png',
            bio TEXT DEFAULT ''
        )
    """)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN bio TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

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
            rating INTEGER DEFAULT 5 CHECK (rating BETWEEN 1 AND 5),
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

    # Bảng comment
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES food_posts(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Bảng react (like)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            UNIQUE (post_id, user_id),
            FOREIGN KEY (post_id) REFERENCES food_posts(id),
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
        default_avatar = "images/default-avatar.png"
        cursor.execute("INSERT INTO users (username, email, password, verified, avatar) VALUES (?, ?, ?, 1, ?)",
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

def add_food_post(user_id, food_name, description, image_filename, rating=5):
    conn = get_db_connection()
    posted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""
        INSERT INTO food_posts (user_id, food_name, description, image_filename, rating, posted_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, food_name, description, image_filename, rating, posted_at))

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

        default_avatar = "images/default-avatar.png"

        cursor.execute("INSERT INTO users (username, email, password, verified, avatar) VALUES (?, ?, ?, 1, ?)",
                       (username, email, hashed_password, default_avatar))
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

    # Truy vấn đơn giản, không JOIN
    rows = cursor.execute("""
        SELECT place_id, place_name, created_at
        FROM favorites
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,)).fetchall()

    conn.close()

    # Trả về danh sách dict cơ bản
    return [dict(row) for row in rows]


def delete_food_post(post_id, user_id):
    """Xóa bài viết nếu bài viết đó thuộc về user hiện tại"""
    conn = get_db_connection()
    try:
        # Chỉ xóa nếu id bài viết và user_id khớp (bảo mật)
        conn.execute("DELETE FROM food_posts WHERE id = ? AND user_id = ?", (post_id, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Lỗi xóa bài: {e}")
        return False
    finally:
        conn.close()


def remove_favorite(user_id, place_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM favorites 
        WHERE user_id = ? AND place_id = ?
    """, (user_id, place_id))

    conn.commit()
    conn.close()


# database.py

# ✅ FIX: Đổi tên và thêm tham số search_term
def get_feed(limit=10, offset=0, search_term=None): 
    conn = get_db_connection()
    # Lấy user_id, mặc định là 0 nếu chưa đăng nhập
    user_id = session.get("user_id", 0) 
    
    # 1. Base Query (Giữ nguyên các truy vấn con dùng reactions/comments)
    query = """
        SELECT 
            fp.id, fp.food_name, fp.description, fp.image_filename, fp.posted_at, fp.rating,
            u.username, u.avatar,
            (SELECT COUNT(*) FROM reactions r WHERE r.post_id = fp.id) AS like_count,
            (SELECT COUNT(*) FROM comments c WHERE c.post_id = fp.id) AS comment_count,
            EXISTS (
                SELECT 1 FROM reactions r2 
                WHERE r2.post_id = fp.id 
                AND r2.user_id = ?
            ) AS is_liked
        FROM food_posts fp
        JOIN users u ON fp.user_id = u.id
    """
    
    params = [user_id] # Tham số đầu tiên: user_id cho EXISTS(SELECT 1 ... AND r2.user_id = ?)

    # 2. THÊM ĐIỀU KIỆN TÌM KIẾM
    if search_term:
        query += " WHERE fp.food_name LIKE ?"
        # ✅ FIX: Thêm tham số tìm kiếm vào danh sách tham số
        params.append(f"%{search_term}%")
    
    # 3. SẮP XẾP BÀI VIẾT
    if search_term:
        # Khi tìm kiếm, sắp xếp theo ngày đăng mới nhất
        query += " ORDER BY fp.posted_at DESC"
    else:
        # Mặc định (không tìm kiếm) là sắp xếp ngẫu nhiên
        query += " ORDER BY RANDOM()"
        
    # 4. PHÂN TRANG
    query += " LIMIT ? OFFSET ?"
    # ✅ Thêm limit và offset vào cuối danh sách tham số
    params.extend([limit, offset])

    # Thực thi truy vấn
    rows = conn.execute(query, tuple(params)).fetchall()

    conn.close()
    
    # ... (Phần trả về giữ nguyên)
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "username": row["username"],
            "avatar": row["avatar"],
            "food_name": row["food_name"],
            "description": row["description"],
            "image_filename": row["image_filename"],
            "posted_at": row["posted_at"],
            "rating": row["rating"],
            "like_count": row["like_count"],
            "comment_count": row["comment_count"],
            "is_liked": bool(row["is_liked"])
        })
    return result

# ======================================
# COMMENT FUNCTIONS
# ======================================
# ... (thêm vào cuối file)

def get_comments_by_post(post_id):
    # Dùng hàm chuẩn để lấy kết nối và đảm bảo row_factory
    conn = get_db_connection() 
    
    rows = conn.execute("""
        SELECT c.id, c.content, c.created_at,
               u.username, u.avatar, u.id AS user_id
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.post_id = ?
        ORDER BY c.id DESC
    """, (post_id,)).fetchall()
    
    conn.close()

    # Trả về list of sqlite3.Row objects (dict-like)
    return rows

# ======================================
# USER UPDATE FUNCTIONS (THÊM MỚI)
# ======================================

def update_user_info(user_id, new_username, new_bio):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # --- DEBUG: In ra để xem chuyện gì đang xảy ra ---
        print(f"DEBUG: Đang thử đổi tên User ID {user_id} thành '{new_username}'")
        
        # BƯỚC 1: KIỂM TRA TRÙNG TÊN (Dùng TRIM để loại bỏ dấu cách ẩn trong DB)
        # Logic: Tìm xem có thằng nào (khác mình) có tên GIỐNG Y HỆT không (bỏ qua dấu cách thừa 2 đầu)
        cursor.execute("""
            SELECT id, username FROM users 
            WHERE TRIM(username) = ? AND id != ?
        """, (new_username.strip(), user_id))
        
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"DEBUG: Đã tìm thấy trùng với User ID {existing_user['id']} tên là '{existing_user['username']}'")
            return False, "username_taken"

        # BƯỚC 2: UPDATE
        # Kiểm tra thêm 1 lần nữa ở tầng database catch lỗi
        cursor.execute("""
            UPDATE users 
            SET username = ?, bio = ? 
            WHERE id = ?
        """, (new_username.strip(), new_bio, user_id))
        
        conn.commit()
        print("DEBUG: Cập nhật thành công!")
        return True, "success"

    except sqlite3.IntegrityError:
        print("DEBUG: Lỗi IntegrityError (UNIQUE constraint) đã bắt được!")
        return False, "username_taken"
        
    except Exception as e:
        print(f"Lỗi update profile: {e}")
        return False, "error"
        
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized with OTP + Favorites support.")
