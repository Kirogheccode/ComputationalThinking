import sqlite3
from flask import jsonify
import openrouteservice
import os
from dotenv import load_dotenv
import requests

load_dotenv()
ORS_API_KEY = os.getenv("ORS_API_KEY")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API")
ors_client = openrouteservice.Client(key=ORS_API_KEY)


def geocode_address(address: str):
    """
    Chỉ dùng để geocode địa chỉ người dùng nhập (origin)
    """
    if not GEOAPIFY_API_KEY:
        raise ValueError("GEOAPIFY_API_KEY not found")

    url = "https://api.geoapify.com/v1/geocode/search"
    params = {
        "text": address,
        "apiKey": GEOAPIFY_API_KEY,
        "limit": 1
    }
    res = requests.get(url, params=params)
    data = res.json()

    if res.status_code != 200:
        raise Exception(f"Lỗi kết nối Geoapify: {res.status_code}")

    if "features" in data and data["features"]:
        lon, lat = data["features"][0]["geometry"]["coordinates"]
        return lat, lon
    else:
        raise ValueError(f"Không tìm thấy toạ độ cho địa chỉ: {address}")


def get_coordinates_from_db(location: str):
    """
    Lấy trực tiếp Latitude/Longitude của nhà hàng từ SQLite
    Cập nhật: Sửa tên bảng và cột thành chữ thường để khớp với foody_data.sqlite mới
    """
    # Đảm bảo đường dẫn file database chính xác
    db_path = 'data/foody_data.sqlite' 
    if not os.path.exists(db_path):
        # Fallback nếu file nằm cùng cấp thư mục
        db_path = 'data/foody_data.sqlite'
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # SỬA Ở ĐÂY: Tên bảng 'restaurants' và cột viết thường
    cursor.execute("SELECT latitude, longitude FROM restaurants WHERE location = ?", (location,))
    row = cursor.fetchone()
    conn.close()

    if row:
        # SỬA Ở ĐÂY: Truy xuất key viết thường
        return row["latitude"], row["longitude"]
    else:
        return None, None


def get_route(user_lat: float, user_lon: float, dest_lat: float, dest_lon: float):
    """
    Lấy tuyến đường từ OpenRouteService giữa hai điểm
    """
    try:
        coords = [(user_lon, user_lat), (dest_lon, dest_lat)]
        route = ors_client.directions(
            coordinates=coords,
            profile="driving-car",
            format="geojson"
        )
        return route["features"][0]["geometry"] 
        
    except Exception as e:
        raise Exception(f"Lỗi khi tính route bằng ORS: {e}")


def drawMarkerByCoordinate(data):
    try:
        location = data.get('address')
        if not location:
            return jsonify({'error': 'Thiếu địa chỉ'}), 400

        # Lấy tọa độ nhà hàng từ DB
        lat, lon = get_coordinates_from_db(location)
        
        # Nếu DB không có (ví dụ quán mới chưa crawl), fallback sang Geoapify
        if lat is None:
            print(f"Không tìm thấy '{location}' trong DB, đang gọi Geoapify...")
            lat, lon = geocode_address(location)

        return jsonify({'lat': lat, 'lng': lon})
    except Exception as e:
        print(f"Lỗi Geocode: {e}")
        return jsonify({'lat': None, 'lng': None, 'error': str(e)})


def drawPathToDestionation(data):
    origin_text = data.get('origin')
    destination_text = data.get('destination')

    if not origin_text or not destination_text:
        return jsonify({'error': 'Thiếu địa chỉ đi hoặc đến'}), 400

    try:
        # 1. Lấy tọa độ người dùng (luôn dùng Geoapify vì là vị trí bất kỳ)
        user_lat, user_lon = geocode_address(origin_text)

        # 2. Lấy tọa độ điểm đến (ưu tiên lấy từ DB cho chính xác)
        dest_lat, dest_lon = get_coordinates_from_db(destination_text)
        
        if dest_lat is None:
            try:
                dest_lat, dest_lon = geocode_address(destination_text)
            except Exception:
                return jsonify({'error': 'Không tìm thấy tọa độ điểm đến'}), 404

        # 3. Tính toán đường đi
        route_geometry = get_route(user_lat, user_lon, dest_lat, dest_lon)

        return jsonify({
            'geometry': route_geometry,
            'start_point': [user_lat, user_lon],
            'end_point': [dest_lat, dest_lon]
        })
    except Exception as e:
        print(f"Lỗi tìm đường: {e}")
        return jsonify({'error': str(e)}), 500