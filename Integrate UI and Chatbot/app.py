from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for
import Routing
import SearchModule
from auth import auth_bp, login_required # Import auth blueprint và decorator
from database import init_db, add_food_post, get_food_posts_by_user, get_user_by_id # Import các hàm DB mới
import os
from werkzeug.utils import secure_filename


# Khởi tạo ứng dụng Flask
app = Flask(__name__)

# Cấu hình Secret Key cho session
# Rất quan trọng cho bảo mật, thay đổi chuỗi này trong môi trường production!
app.config['SECRET_KEY'] = 'your_super_secret_key_here_for_session_management' 

# Cấu hình thư mục tải lên ảnh
UPLOAD_FOLDER = 'Integrate UI and Chatbot/static/images/user_uploads'
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
foods = {
    'pho': {
        'name': 'Phở Bò',
        'description': 'Phở là một món ăn truyền thống của Việt Nam, được xem là một trong những món ăn tiêu biểu cho ẩm thực Việt Nam. Thành phần chính của phở là bánh phở và nước dùng cùng với thịt bò hoặc gà cắt lát mỏng.',
        'location': 'Phở Thìn - 13 Lò Đúc, Hà Nội',
        'price': '50,000 - 70,000 VNĐ',
        'image': 'images/mainpage-display/pho.jpg'
    },
    'banh_mi': {
        'name': 'Bánh Mì',
        'description': 'Bánh mì Việt Nam là một loại bánh mì baguette được xẻ dọc, nhồi với thịt, πατέ, rau, và các loại nước sốt. Đây là một món ăn đường phố phổ biến và được yêu thích trên toàn thế giới.',
        'location': 'Bánh mì Phượng - 2B Phan Chu Trinh, Hội An',
        'price': '25,000 - 40,000 VNĐ',
        'image': 'images/mainpage-display/banh_mi.jpg'
    },
    'bun_cha': {
        'name': 'Bún Chả',
        'description': 'Bún chả là một món ăn của Hà Nội, bao gồm bún, chả thịt lợn nướng trên than hoa và bát nước mắm chua cay mặn ngọt. Món ăn này thường được ăn kèm với các loại rau sống.',
        'location': 'Bún chả Hương Liên - 24 Lê Văn Hưu, Hà Nội',
        'price': '40,000 - 60,000 VNĐ',
        'image': 'images/mainpage-display/bun_cha.jpg'
    }
}

# Route cho trang chủ
@app.route('/')
def index():
    """
    Hiển thị trang chủ với danh sách các món ăn nổi bật.
    """
    return render_template('index.html', foods=foods)

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

    user_posts = get_food_posts_by_user(user_id)
    return render_template('account.html', username=username, posts=user_posts)


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
    data = request.get_json()
    return SearchModule.replyToUser(data)

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
    
# Chạy ứng dụng
if __name__ == '__main__':
    app.run(debug=True, port=5000)