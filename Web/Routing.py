import sqlite3
from flask import jsonify
import openrouteservice
import os
from dotenv import load_dotenv
import requests

load_dotenv()
ORS_API_KEY = os.getenv("ORS_API_KEY")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
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
    Kết nối vào bảng restaurants để lấy dữ liệu vị trí
    """
    db_path = 'data/foody_data.sqlite'
    if not os.path.exists(db_path):
        db_path = 'data/foody_data.sqlite'
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT latitude, longitude FROM restaurants WHERE location = ?", (location,))
    row = cursor.fetchone()
    conn.close()

    if row:
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
    """
    Xử lý API lấy tọa độ để vẽ marker lên bản đồ.
    Kiểm tra địa chỉ trong database trước, nếu không có sẽ dùng Geoapify.
    """
    try:
        location = data.get('address')
        if not location:
            return jsonify({'error': 'Thiếu địa chỉ'}), 400

        lat, lon = get_coordinates_from_db(location)
        
        if lat is None:
            print(f"Không tìm thấy '{location}' trong DB, đang gọi Geoapify...")
            lat, lon = geocode_address(location)

        return jsonify({'lat': lat, 'lng': lon})
    except Exception as e:
        print(f"Lỗi Geocode: {e}")
        return jsonify({'lat': None, 'lng': None, 'error': str(e)})


def drawPathToDestionation(data):
    """
    Xử lý API vẽ đường đi từ điểm xuất phát (người dùng nhập) đến điểm đến.
    Bao gồm kiểm tra tính hợp lệ của địa chỉ đầu vào.
    """
    origin_text = data.get('origin')
    destination_text = data.get('destination')

    if not origin_text or not destination_text:
        return jsonify({'error': 'Thiếu địa chỉ đi hoặc đến'}), 400

    try:
        float(origin_text)
        return jsonify({'error': 'Địa chỉ xuất phát không hợp lệ'}), 400
    except ValueError:
        pass

    try:
        user_lat, user_lon = geocode_address(origin_text)

        dest_lat, dest_lon = get_coordinates_from_db(destination_text)
        
        if dest_lat is None:
            try:
                dest_lat, dest_lon = geocode_address(destination_text)
            except Exception:
                return jsonify({'error': 'Không tìm thấy tọa độ điểm đến'}), 404

        route_geometry = get_route(user_lat, user_lon, dest_lat, dest_lon)

        return jsonify({
            'geometry': route_geometry,
            'start_point': [user_lat, user_lon],
            'end_point': [dest_lat, dest_lon]
        })
    except Exception as e:
        print(f"Lỗi tìm đường: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    testing_address = "123123 Nguyễn Hoàng Cừ"
    testing_lat, testing_lon = geocode_address(testing_address)
    print(f"Địa chỉ: {testing_address}\nToạ độ: {testing_lat}, {testing_lon}")