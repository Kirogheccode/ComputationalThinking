from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for
import os
import math
import re # Import re để dùng trong search
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime
import sqlite3

# Import các module tự viết
import Routing
import Currency  # Import the new file
from FoodRecognition import replyToImage
from auth import auth_bp, login_required
from FoodLoading import load_foods_from_sqlite
from Search_Clone_2 import replyToUser
from extensions import oauth
from lang import translations
from database import (
    init_db, add_food_post, get_food_posts_by_user, get_user_by_id,
    add_favorite, get_favorites_by_user, remove_favorite, delete_food_post,
    get_feed, get_db_connection, get_comments_by_post, update_user_info
)
from SaveAnswer import queryAnswerForUser, resetDB

# Load environment variables
load_dotenv()

# Khởi tạo ứng dụng Flask
app = Flask(__name__)

# Cấu hình bảo mật
# Lấy SECRET_KEY từ .env, nếu không có thì dùng chuỗi mặc định (chỉ dùng cho dev)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev_secret_key_12345") 

# Khởi tạo OAuth
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # Chỉ dùng khi chạy localhost (HTTP)
oauth.init_app(app)

# Cấu hình thư mục upload
UPLOAD_FOLDER = os.path.join(app.root_path, "static/images/user_uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Cấu hình thư mục user avatar
app.config['AVATAR_UPLOAD_FOLDER'] = 'static/images/avatars'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Đăng ký blueprint
app.register_blueprint(auth_bp)

# --- XỬ LÝ NGÔN NGỮ ---
@app.context_processor
def inject_lang():
    """Truyền biến ngôn ngữ vào tất cả các template"""
    lang = session.get("lang", "vi") # Mặc định là tiếng Việt
    return dict(t=translations[lang], current_lang=lang, lang=translations[lang]) 
    # Lưu ý: Trả về cả 't' và 'lang' để tương thích với code HTML cũ của bạn (dùng {{ lang.home }})

@app.route('/set-language/<lang_code>')
def set_language(lang_code):
    """Route để chuyển đổi ngôn ngữ khi bấm vào cờ"""
    if lang_code in translations:
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('index'))

# --- HÀM HỖ TRỢ ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Khởi tạo DB và Load dữ liệu
with app.app_context():
    init_db()
    foods_data = load_foods_from_sqlite() # Load 1 lần khi start app

# --- ROUTES CHÍNH ---

@app.route("/")
def index():
    page = int(request.args.get("page", 1))
    area = request.args.get("area", "all").strip()
    q = request.args.get("q", "").strip().lower()

    favorite_ids = []
    if 'user_id' in session:
        user_favs = get_favorites_by_user(session['user_id'])
        favorite_ids = [str(item['place_id']) for item in user_favs]
    # ---------------------------------------------------------

    filtered_foods = []
    for food in foods_data:
        location = food["location"].strip()
        name = food["name"].strip().lower()

        if area.lower() != "all":
            pattern = r'\b{}\b'.format(re.escape(area.lower()))
            if not re.search(pattern, location.lower()):
                continue

        if q and q not in name:
            continue

        filtered_foods.append(food)

    per_page = 9
    total_pages = math.ceil(len(filtered_foods) / per_page)
    foods_to_render = filtered_foods[(page-1)*per_page : page*per_page]

    return render_template(
        "index.html",
        foods=foods_to_render,
        page=page,
        total_pages=total_pages,
        area_selected=area,
        search_query=q,
        favorite_ids=favorite_ids  
    )

@app.route('/map')
def map_page():
    return render_template('map.html')

@app.route('/chatbot')
def chatbot_page():
    resetDB()
    return render_template('chatbot.html')

@app.route('/forum')
def forum_page():
    page = int(request.args.get("page", 1))
    area = request.args.get("area", "all").strip()
    q = request.args.get("q", "").strip().lower()

    favorite_ids = []
    if 'user_id' in session:
        user_favs = get_favorites_by_user(session['user_id'])
        favorite_ids = [str(item['place_id']) for item in user_favs]

    filtered_foods = []
    for food in foods_data:
        location = food["location"].strip()
        name = food["name"].strip().lower()

        # Lọc theo khu vực
        if area.lower() != "all":
            pattern = r'\b{}\b'.format(re.escape(area.lower()))
            if not re.search(pattern, location.lower()):
                continue

        # Lọc theo từ khóa tìm kiếm
        if q and q not in name:
            continue

        filtered_foods.append(food)

    # Phân trang
    per_page = 9
    total_pages = math.ceil(len(filtered_foods) / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    foods_to_render = filtered_foods[start:end]

    return render_template(
        "forum.html",
        foods=foods_to_render,
        page=page,
        total_pages=total_pages,
        area_selected=area,
        search_query=q,
        favorite_ids=favorite_ids  
    )

@app.route('/exchange')
def exchange_page():
    # Pass the supported currencies to the template so we don't hardcode them in HTML
    return render_template('exchange.html', currencies=Currency.SUPPORTED_CURRENCIES)

@app.route('/account')
@login_required
def account_page():
    user_id = session['user_id']

    user = get_user_by_id(user_id)
    
    # Cập nhật lại session username nếu trong DB khác session (phòng trường hợp vừa đổi tên xong)
    if user and user['username'] != session.get('username'):
        session['username'] = user['username']

    username = user['username']
    user_bio = user['bio'] if user['bio'] else ""

    user_posts = get_food_posts_by_user(user_id)
    raw_favorites = get_favorites_by_user(user_id) 

    enriched_favorites = []
    for fav in raw_favorites:
        fav_id = str(fav['place_id'])
        found_food = next((f for f in foods_data if str(f['id']) == fav_id), None)
        
        if found_food:
            enriched_favorites.append({
                "place_id": fav['place_id'],
                "place_name": fav['place_name'],
                "created_at": fav['created_at'],
                "image": found_food['image'],
                "location": found_food['location'],
                "rating": found_food['rating'],
                "price": found_food.get('price', 'Updating'), # Thêm fallback
                "hours": found_food.get('hours', 'Updating')
            })
        else:
            enriched_favorites.append({
                "place_id": fav['place_id'],
                "place_name": fav['place_name'],
                "created_at": fav['created_at'],
                "image": "images/default_food.jpg", # Ảnh mặc định nếu không tìm thấy
                "location": "Thông tin chưa cập nhật",
                "rating": "N/A",
                "price": "",
                "hours": ""
            })

    user = get_user_by_id(user_id)

    avatar_url = (
        url_for('static', filename=user['avatar'])
        if user and user['avatar']
        else url_for('static', filename='images/default-avatar.jpg')
    )

    return render_template(
        'account.html',
        user=user, 
        username=username,
        user_bio=user_bio,
        avatar_url=avatar_url,
        posts=user_posts,
        favorites=enriched_favorites
    )

@app.route('/account', methods=['POST'])
@login_required
def your_account():
    user_id = session['user_id']
    food_name = request.form['food_name']
    description = request.form['description']
    image_file = request.files.get('image')
    rating = int(request.form.get("rating", 5))

    if not food_name or not description:
        flash('Vui lòng điền tên món ăn và đánh giá.', 'danger')
        return redirect(url_for('account_page')) # Sửa lại redirect về account_page cho đúng tên hàm
    
    image_filename = None
    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        # Lưu file
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(save_path)
        # Lưu đường dẫn vào DB (dạng relative path để static url_for dùng được)
        image_filename = f"images/user_uploads/{filename}"
    
    add_food_post(user_id, food_name, description, image_filename, rating)
    flash('Bài đăng của bạn đã được thêm thành công!', 'success')
    return redirect(url_for('account_page'))


@app.route('/post/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    user_id = session['user_id']
    if delete_food_post(post_id, user_id):
        flash('Đã xóa bài viết thành công.', 'success')
    else:
        flash('Không thể xóa bài viết này.', 'danger')
    return redirect(url_for('account_page'))

@app.route('/account/update-info', methods=['POST'])
@login_required
def update_info():
    user_id = session['user_id']
    new_username = request.form.get('username').strip()
    new_bio = request.form.get('bio').strip()
    
    current_lang = session.get("lang", "vi")

    if not new_username:
        flash(translations[current_lang]['input_required'], 'danger')
        return redirect(url_for('account_page'))

    success, message_code = update_user_info(user_id, new_username, new_bio)

    if success:
        # Cập nhật lại session username ngay lập tức
        session['username'] = new_username
        flash(translations[current_lang]['update_success'], 'success')
    else:
        if message_code == "username_taken":
            flash(translations[current_lang]['username_taken'], 'danger')
        else:
            flash("Error updating profile", 'danger')

    return redirect(url_for('account_page'))

# --- API ROUTES ---

@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.get_json()
        result = replyToUser(data)
        return jsonify(result)
    except Exception as e:
        print("Lỗi xử lý chat:", e)
        return jsonify({"reply": "Hệ thống đang bận, vui lòng thử lại sau.", "food_data": []}), 500

@app.route('/api/find_path', methods=['POST'])
def find_path():
    data = request.get_json()
    return Routing.drawPathToDestionation(data)
    
@app.route('/api/geocode', methods=['POST'])
def get_coordinates(): 
    data = request.get_json()
    return Routing.drawMarkerByCoordinate(data)

@app.route('/api/predict', methods=['POST'])
def predict_food():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    img_file = request.files["image"]
    return replyToImage(img_file)


# --- CURRENCY API ---
@app.route('/api/convert_currency', methods=['POST'])
def api_convert_currency():
    data = request.get_json()

    # Get data from frontend
    currency_code = data.get('currency')
    amount = data.get('amount')
    direction = data.get('direction') # '1' or '2'

    # Validation
    if not currency_code or not amount or not direction:
        return jsonify({"success": False, "error": "Missing data"})

    try:
        amount = float(amount)
    except ValueError:
        return jsonify({"success": False, "error": "Invalid amount"})

    # Call the logic from Currency.py
    result = Currency.calculate_conversion(amount, currency_code, direction)

    return jsonify(result)


@app.route('/api/scan_money', methods=['POST'])
def api_scan_money():
    if 'image' not in request.files:
        return jsonify({"success": False, "error": "No image uploaded"})

    file = request.files['image']
    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected"})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Save temporarily
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Call Gemini logic
        result = Currency.scan_money_image(filepath)

        # Clean up (delete) the file after scanning to save space
        try:
            os.remove(filepath)
        except:
            pass

        return jsonify(result)

    return jsonify({"success": False, "error": "Invalid file type"})
# --- SHOW PREVIOUS ANSWER ---
@app.route("/api/showanswer",methods=["POST"])
def api_show_answer():
    if 'user_id' not in session:
        return jsonify({"message": "Please login to use save answer function!"}), 401
    
    data = request.get_json()
    return jsonify(queryAnswerForUser(data))

# --- FAVORITE API ---

@app.route("/favorite/add", methods=["POST"])
def api_add_favorite():
    if 'user_id' not in session:
        return jsonify({"status": "unauthorized"}), 401 # Frontend sẽ redirect

    data = request.get_json()
    place_id = data.get("place_id")
    place_name = data.get("place_name")

    if not place_id or not place_name:
        return jsonify({"error": "Missing data"}), 400

    add_favorite(session["user_id"], place_id, place_name)
    return jsonify({"status": "success"})

@app.route("/favorite/remove", methods=["POST"])
@login_required
def api_remove_favorite():
    data = request.get_json()
    place_id = data.get("place_id")
    if not place_id:
        return jsonify({"error": "Missing place_id"}), 400
        
    remove_favorite(session["user_id"], place_id)
    return jsonify({"status": "success"})

@app.route("/api/feed")
def api_feed():
    
    page = request.args.get("page", 1, type=int)
    limit = 10
    offset = (page - 1) * limit
    
    # ✅ LẤY TỪ KHÓA TÌM KIẾM TỪ REQUEST
    search_term = request.args.get("search", "")

    # ✅ GỌI HÀM get_feed MỚI VÀ TRUYỀN CẢ LIMIT, OFFSET VÀ SEARCH_TERM
    posts = get_feed(limit, offset, search_term)

    return jsonify(posts)

@app.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    user_id = session['user_id']
    file = request.files.get('avatar')

    if not file or file.filename == '':
        flash("Vui lòng chọn ảnh", "danger")
        return redirect(url_for("account_page"))

    if not allowed_file(file.filename):
        flash("Chỉ được upload ảnh (png, jpg, jpeg)", "danger")
        return redirect(url_for("account_page"))

    # Đặt tên file theo user id để tránh trùng
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"user_{user_id}.{ext}"

    save_path = os.path.join(app.config['AVATAR_UPLOAD_FOLDER'], filename)
    file.save(save_path)

    avatar_db_path = f"images/avatars/{filename}"

    # ✅ UPDATE VÀO DB
    conn = get_db_connection()
    conn.execute(
        "UPDATE users SET avatar = ? WHERE id = ?",
        (avatar_db_path, user_id)
    )
    conn.commit()
    conn.close()

    flash("✅ Đổi avatar thành công!", "success")
    return redirect(url_for("account_page"))

# Tính năng like
@app.route("/toggle-like/<int:post_id>", methods=["POST"])
def toggle_like(post_id):
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    user_id = session["user_id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM reactions 
        WHERE post_id = ? AND user_id = ?
    """, (post_id, user_id))

    liked = cursor.fetchone()

    if liked:
        cursor.execute("""
            DELETE FROM reactions 
            WHERE post_id = ? AND user_id = ?
        """, (post_id, user_id))
        status = "unliked"
    else:
        cursor.execute("""
            INSERT INTO reactions (post_id, user_id)
            VALUES (?, ?)
        """, (post_id, user_id))
        status = "liked"

    conn.commit()

    cursor.execute("""
        SELECT COUNT(*) FROM reactions WHERE post_id = ?
    """, (post_id,))
    total_likes = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "status": status,
        "total_likes": total_likes
    })

#Tính năng comment
@app.route("/comment/add/<int:post_id>", methods=["POST"])
def add_comment(post_id):

    if "user_id" not in session:
        return jsonify({"success": False})

    content = request.form.get("content")

    if not content or content.strip() == "":
        return jsonify({"success": False})

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("data/smart_tourism.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO comments (post_id, user_id, content, created_at)
        VALUES (?, ?, ?, ?)
    """, (post_id, session["user_id"], content, created_at))

    conn.commit()
    comment_id = cursor.lastrowid

    cursor.execute("""
        SELECT comments.id, comments.content, users.username, users.avatar
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.id = ?
    """, (comment_id,))

    cmt = cursor.fetchone()
    conn.close()

    return jsonify({
        "success": True,
        "comment": {
            "id": cmt[0],
            "content": cmt[1],
            "username": cmt[2],
            "avatar": cmt[3]
        }
    })

@app.route("/comment/delete/<int:comment_id>", methods=["POST"])
def delete_comment(comment_id):

    if "user_id" not in session:
        return jsonify({"success": False})

    conn = sqlite3.connect("data/smart_tourism.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id FROM comments WHERE id = ?
    """, (comment_id,))

    owner = cursor.fetchone()

    if not owner or owner[0] != session["user_id"]:
        conn.close()
        return jsonify({"success": False})

    cursor.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route("/comment/list/<int:post_id>")
def get_comment_list(post_id):

    # ✅ GỌI HÀM TỪ DATABASE.PY
    rows = get_comments_by_post(post_id) 

    data = []
    for r in rows:
        # ✅ TRUY CẬP DỮ LIỆU BẰNG TÊN CỘT (vì đã dùng get_db_connection() trong database.py)
        data.append({
            "id": r["id"],
            "content": r["content"],
            "username": r["username"],
            "avatar": r["avatar"],
            "user_id": r["user_id"]
        })

    return jsonify(data)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)