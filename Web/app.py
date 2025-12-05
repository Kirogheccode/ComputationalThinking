from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for
import Routing
from FoodRecognition import replyToImage
from auth import auth_bp, login_required # Import auth blueprint và decorator
import os
from FoodLoading import load_foods_from_sqlite
import math
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
from werkzeug.utils import secure_filename
from Search_Clone_2 import replyToUser
from extensions import oauth
from lang import translations
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

@app.context_processor
def inject_lang():
    lang = request.args.get("lang") or session.get("lang") or "vi"
    session["lang"] = lang
    return dict(t=translations[lang], current_lang=lang)

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
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Khởi tạo database khi ứng dụng chạy
with app.app_context():
    init_db()

# Dữ liệu mẫu về các món ăn
# Trong một dự án thực tế, dữ liệu này nên được lấy từ database
foods_data = load_foods_from_sqlite("foody_data.sqlite")

@app.route("/")
def index():
    import re
    page = int(request.args.get("page", 1))
    area = request.args.get("area", "all").strip()
    q = request.args.get("q", "").strip().lower()

    # --- ĐOẠN MỚI THÊM: Lấy danh sách ID quán đã yêu thích ---
    favorite_ids = []
    if 'user_id' in session:
        # Lấy list dict favorites, sau đó trích xuất place_id ra list riêng
        # Lưu ý: Chuyển về string để dễ so sánh trong template
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
        favorite_ids=favorite_ids  # <--- Truyền biến này sang HTML
    )

# Route cho trang bản đồ
@app.route('/map')
def map_page():
    """
    Hiển thị trang bản đồ.
    """
    return render_template('map.html')

# Route cho trang chatbot
@app.route('/chatbot')
def chatbot_page():
    """
    Hiển thị trang chatbot.
    """
    return render_template('chatbot.html')

# Route cho trang giới thiệu
@app.route('/about')
def about_page():
    """
    Hiển thị trang giới thiệu dự án.
    """
    return render_template('about.html')

# Route cho trang tài khoản người dùng (chỉ khi đăng nhập hàm mới chạy)
@app.route('/account')
@login_required
def account_page():
    user_id = session['user_id']
    username = session['username']

    # 1. Lấy các bài viết
    user_posts = get_food_posts_by_user(user_id)
    
    # 2. Lấy danh sách yêu thích thô (chỉ có ID, tên, ngày)
    raw_favorites = get_favorites_by_user(user_id) 

    # 3. Ghép thông tin chi tiết (Ảnh, Rating, Địa chỉ) từ foods_data
    enriched_favorites = []
    
    for fav in raw_favorites:
        fav_id = str(fav['place_id']) # Chuyển về string để so sánh
        
        # Tìm món ăn trong foods_data khớp ID
        # (foods_data là biến toàn cục đã load từ FoodLoading.py ở đầu file)
        found_food = next((f for f in foods_data if str(f['id']) == fav_id), None)
        
        if found_food:
            # Nếu tìm thấy, lấy thông tin chi tiết bỏ vào
            enriched_favorites.append({
                "place_id": fav['place_id'],
                "place_name": fav['place_name'],
                "created_at": fav['created_at'],
                "image": found_food['image'],       # Lấy ảnh
                "location": found_food['location'], # Lấy địa chỉ
                "rating": found_food['rating']      # Lấy rating
            })
        else:
            # Dự phòng nếu không tìm thấy (ví dụ quán đã bị xóa khỏi data gốc)
            enriched_favorites.append({
                "place_id": fav['place_id'],
                "place_name": fav['place_name'],
                "created_at": fav['created_at'],
                "image": "images/restaurant_placeholder.jpg",
                "location": "Thông tin chưa cập nhật",
                "rating": "N/A"
            })

    # Truyền danh sách đã ghép (enriched_favorites) sang template
    return render_template('account.html', username=username, posts=user_posts, favorites=enriched_favorites)


# User đăng bài đánh giá các món ăn, kết quả trả về là quay lại trang your_account
@app.route('/account', methods=['POST'])
@login_required
def your_account():
    user_id = session['user_id']
    
    food_name = request.form['food_name']
    description = request.form['description']
    image_file = request.files.get('image')

    if not food_name or not description:
        flash('Vui lòng điền tên món ăn và đánh giá.', 'danger')
        return redirect(url_for('your_account'))
    
    image_filename = None
    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        image_filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_filename)
        # Lưu đường dẫn tương đối để dễ hiển thị trên web
        image_filename = os.path.join('images/user_uploads', filename) 
    
    add_food_post(user_id, food_name, description, image_filename)
    flash('Bài đăng của bạn đã được thêm thành công!', 'success')
    return redirect(url_for('your_account'))



# Phản hồi câu hỏi của user (Gemini + OpenStreetMap + Geoapify) về quán ăn
@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.get_json()
        result = replyToUser(data)
        return jsonify(result)

    except Exception as e:
        print("Lỗi xử lý chat:", e)
        return jsonify({
            "reply": "Xin lỗi, hệ thống đang gặp sự cố.",
            "food_data": []
        }), 500

# Tìm đường ngắn nhất tới quán ăn (ORS) qua vị trí user nhập vào
@app.route('/api/find_path', methods=['POST'])
def find_path():
    data = request.get_json()
    return Routing.drawPathToDestionation(data)
    
# Chuyển đổi địa chỉ qua toạ độ (GOOING) để vẽ marker lên bản đồ
@app.route('/api/geocode', methods=['POST'])
def get_coordinates(): 
    data = request.get_json()
    return Routing.drawMarkerByCoordinate(data)

# Nhận ảnh thức ăn và nhận diện
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
