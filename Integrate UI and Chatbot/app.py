from flask import Flask, render_template, request, jsonify
import SearchModule
import Routing

# Khởi tạo ứng dụng Flask
app = Flask(__name__)

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


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """
    Nhận tin nhắn từ JavaScript, gọi SearchModule, và trả về kết quả.
    """
    try:
        # 1. Nhận dữ liệu JSON từ request
        data = request.get_json()
        user_message = data.get('message')

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # 2. Gọi hàm logic từ SearchModule
        restaurant_list = SearchModule.restaurantSuggest(user_message)

        # 3. Định dạng kết quả trả về
        if not restaurant_list:
            response_text = "Xin lỗi, mình không tìm thấy nhà hàng nào phù hợp với yêu cầu của bạn. Bạn thử tìm ở khu vực khác xem?"
        else:
            # Biến danh sách nhà hàng thành một chuỗi văn bản đẹp
            response_text = "Mình tìm thấy vài gợi ý cho bạn nè:\n\n"
            for r in restaurant_list:
                # Dùng **để in đậm (Markdown)
                response_text += f"{r['Name']}\n" 
                response_text += f"Địa chỉ: {r['Address']}\n"
                response_text += f"Giờ mở cửa: {r['OpeningTime']}\n"
                response_text += f"Ẩm thực: {r['Cuisine']}\n\n"
        
        # 4. Trả về kết quả dạng JSON
        # JavaScript của bạn sẽ nhận được {'reply': response_text}
        response = {"food_data": restaurant_list}
        print("JSON response:", response)  # Debug trước khi jsonify
        return jsonify(response)

    except Exception as e:
        print(f"Lỗi tại /api/chat: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/find_path', methods=['POST'])
def find_path():
    data = request.get_json()
    origin_text = data.get('origin')       # Địa chỉ người dùng nhập
    destination_text = data.get('destination') # Địa chỉ quán ăn (lấy từ nút bấm)

    if not origin_text or not destination_text:
        return jsonify({'error': 'Thiếu địa chỉ đi hoặc đến'}), 400

    try:
        # 1. Chuyển đổi địa chỉ sang tọa độ (Geocoding)
        # (Dùng hàm geocode_address trong Routing.py của bạn)
        user_lat, user_lon = Routing.geocode_address(origin_text)
        dest_lat, dest_lon = Routing.geocode_address(destination_text)

        # 2. Tìm đường đi (Routing)
        # (Dùng hàm get_route trong Routing.py)
        route_geometry = Routing.get_route(user_lat, user_lon, dest_lat, dest_lon)
        
        # Trả về geometry để JS vẽ đường
        return jsonify({
            'geometry': route_geometry,
            'start_point': [user_lat, user_lon],
            'end_point': [dest_lat, dest_lon]
        })

    except Exception as e:
        print(f"Lỗi tìm đường: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/geocode', methods=['POST'])
def get_coordinates():
    """
    API nhận địa chỉ (text) và trả về tọa độ (lat, lng)
    để frontend vẽ marker ngay lập tức.
    """
    try:
        data = request.get_json()
        address = data.get('address')
        
        if not address:
            return jsonify({'error': 'Thiếu địa chỉ'}), 400

        # Gọi hàm geocode_address có sẵn trong Routing.py
        lat, lon = Routing.geocode_address(address)
        
        return jsonify({'lat': lat, 'lng': lon})

    except Exception as e:
        print(f"Lỗi Geocode: {e}")
        # Trả về null nếu không tìm thấy, để frontend biết mà xử lý
        return jsonify({'lat': None, 'lng': None, 'error': str(e)})
    
# chay ung dung
if __name__ == '__main__':
    app.run(debug=True, port=5000)