from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for
import Routing
from FoodRecognition import replyToImage
from auth import auth_bp, login_required
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
from werkzeug.utils import secure_filename
import sys
import requests
from Search_Clone_2 import replyToUser
from extensions import oauth

# Gộp import database vào 1 chỗ (không bỏ bất kỳ hàm nào)
from database import (
    init_db, 
    add_food_post, 
    get_food_posts_by_user, 
    get_user_by_id,
    add_favorite,
    get_favorites_by_user,
    remove_favorite
)

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
oauth.init_app(app)

# Secret key session
app.config['SECRET_KEY'] = 'your_super_secret_key_here_for_session_management' 

# Cấu hình thư mục upload (fix path tuyệt đối)
UPLOAD_FOLDER = os.path.join(app.root_path, "static/images/user_uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Đảm bảo thư mục upload tồn tại
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Đăng ký blueprint xác thực
app.register_blueprint(auth_bp)

# Hàm kiểm tra đuôi file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Khởi tạo database khi ứng dụng chạy
with app.app_context():
    init_db()

# Dữ liệu mẫu về món ăn (giữ nguyên)
foods = {
    'pho': {
        'name': 'Phở Bò',
        'description': 'Phở là một món ăn truyền thống của Việt Nam...',
        'location': 'Phở Thìn - 13 Lò Đúc, Hà Nội',
        'price': '50,000 - 70,000 VNĐ',
        'image': 'images/mainpage-display/pho.jpg'
    },
    'banh_mi': {
        'name': 'Bánh Mì',
        'description': 'Bánh mì Việt Nam là một loại bánh mì baguette...',
        'location': 'Bánh mì Phượng - 2B Phan Chu Trinh, Hội An',
        'price': '25,000 - 40,000 VNĐ',
        'image': 'images/mainpage-display/banh_mi.jpg'
    },
    'bun_cha': {
        'name': 'Bún Chả',
        'description': 'Bún chả là một món ăn của Hà Nội...',
        'location': 'Bún chả Hương Liên - 24 Lê Văn Hưu, Hà Nội',
        'price': '40,000 - 60,000 VNĐ',
        'image': 'images/mainpage-display/bun_cha.jpg'
    }
}

# Trang chủ
@app.route('/')
def index():
    return render_template('index.html', foods=foods)

# Trang bản đồ
@app.route('/map')
def map_page():
    return render_template('map.html')

# Trang chatbot
@app.route('/chatbot')
def chatbot_page():
    return render_template('chatbot.html')

# Trang giới thiệu
@app.route('/about')
def about_page():
    return render_template('about.html')

# Trang tài khoản
@app.route('/account')
@login_required
def account_page():
    user_id = session['user_id']
    username = session['username']
    
    user_posts = get_food_posts_by_user(user_id)
    fav_rows = get_favorites_by_user(user_id)

    # Chuyển sang list of dict
    favorites = [{"place_id": row[0], "place_name": row[1]} for row in fav_rows]

    return render_template('account.html', username=username, posts=user_posts, favorites=favorites)

# Đăng bài đánh giá (rename tránh conflict nhưng giữ nguyên logic)
@app.route('/account', methods=['POST'])
@login_required
def post_account():
    user_id = session['user_id']
    
    food_name = request.form['food_name']
    description = request.form['description']
    image_file = request.files.get('image')

    if not food_name or not description:
        flash('Vui lòng điền tên món ăn và đánh giá.', 'danger')
        return redirect(url_for('post_account'))
    
    image_filename = None
    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        abs_save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(abs_save_path)
        image_filename = os.path.join('images/user_uploads', filename)
    
    add_food_post(user_id, food_name, description, image_filename)
    flash('Bài đăng của bạn đã được thêm thành công!', 'success')
    return redirect(url_for('account_page'))

# Chat API
@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.get_json()
        result = replyToUser(data)
        return jsonify(result)
    except Exception as e:
        print("Lỗi xử lý chat:", e)
        return jsonify({"reply": "Xin lỗi, hệ thống đang gặp sự cố.", "food_data": []}), 500

# ORS tìm đường
@app.route('/api/find_path', methods=['POST'])
def find_path():
    data = request.get_json()
    return Routing.drawPathToDestionation(data)

# Geocode → tọa độ
@app.route('/api/geocode', methods=['POST'])
def get_coordinates(): 
    data = request.get_json()
    return Routing.drawMarkerByCoordinate(data)

# Predict món ăn từ ảnh
@app.route('/api/predict', methods=['POST'])
def predict_food():
    img_file = request.files["image"]
    return replyToImage(img_file)


# ⭐ LƯU NHÀ HÀNG YÊU THÍCH
@app.route("/favorite/add", methods=["POST"])
@login_required
def api_add_favorite():
    data = request.get_json()

    place_id = data.get("place_id")
    place_name = data.get("place_name")

    if not place_id or not place_name:
        return jsonify({"error": "missing place_id or place_name"}), 400

    user_id = session["user_id"]
    add_favorite(user_id, place_id, place_name)

    return jsonify({"status": "success", "message": "Saved to favorites!"})


@app.route("/favorite/list", methods=["GET"])
@login_required
def api_get_favorites():
    user_id = session["user_id"]
    result = get_favorites_by_user(user_id)
    return jsonify(result)


@app.route("/favorite/remove", methods=["POST"])
@login_required
def api_remove_favorite():
    data = request.get_json()
    place_id = data.get("place_id")

    if not place_id:
        return jsonify({"error": "missing place_id"}), 400

    user_id = session["user_id"]
    remove_favorite(user_id, place_id)

    return jsonify({"status": "success"})


# Chạy ứng dụng
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
