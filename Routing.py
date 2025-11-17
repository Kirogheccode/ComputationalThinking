import requests
import openrouteservice
import json
import os
from dotenv import load_dotenv
load_dotenv()
GOONG_API_KEY = os.getenv("GOONG_API_KEY")
ORS_API_KEY = os.getenv("ORS_API_KEY")

ors_client = openrouteservice.Client(key=ORS_API_KEY)


def geocode_address(address: str):
    """
    Giải mã địa chỉ thành toạ độ (vĩ độ, kinh độ) bằng Goong.io API.
    """
    url = "https://rsapi.goong.io/Geocode"
    params = {"address": address, "api_key": GOONG_API_KEY}
    res = requests.get(url, params=params)
    data = res.json()

    if res.status_code != 200:
        raise Exception(f"Lỗi kết nối Goong.io: {res.status_code}")

    if "results" in data and data["results"]:
        loc = data["results"][0]["geometry"]["location"]
        return (loc["lat"], loc["lng"])
    else:
        raise ValueError(f"Không tìm thấy toạ độ cho địa chỉ: {address}")


def get_route(user_lat: float, user_lon: float, dest_lat: float, dest_lon: float):
    """
    Lấy tuyến đường được tính bởi OpenRouteService giữa hai điểm.
    """
    try:
        coords = [(user_lon, user_lat), (dest_lon, dest_lat)]  
        route = ors_client.directions(
            coordinates=coords,
            profile="driving-car",
            format="geojson"
        )
        return route["features"][0]["geometry"]["coordinates"]
    except Exception as e:
        raise Exception(f"Lỗi khi tính route bằng ORS: {e}")


def preprocess_restaurants(user_lat: float, user_lon: float):
    """
    Lưu dữ liệu định tuyến để truy cập, tránh gọi API nhiều lần.
    """
    input_path = "restaurants.json"
    output_path = "restaurants_preprocessed.json"

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Không tìm thấy file {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        restaurants = json.load(f)

    processed = []
    for r in restaurants:
        name = r.get("Name", r.get("Address", "Unknown"))
        try:
            dest_lat, dest_lon = geocode_address(r["Address"])
            route_coords = get_route(user_lat, user_lon, dest_lat, dest_lon)

            r["Coordinates"] = [dest_lat, dest_lon]
            r["Route"] = route_coords

            print(f"Xử lý thành công: {name}")
            processed.append(r)
        except Exception as e:
            print(f"Lỗi xử lý {name}: {e}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)

    print(f"Đã lưu dữ liệu vào {output_path}")


def get_routes_from_json(index: int):
    """
    Lấy dữ liệu tuyến đường đã preprocess từ file JSON.
    """
    file_path = "restaurants_preprocessed.json"
    if not os.path.exists(file_path):
        raise FileNotFoundError("File dữ liệu đã preprocess không tồn tại. Hãy chạy preprocess_restaurants() trước.")

    with open(file_path, "r", encoding="utf-8") as f:
        restaurants = json.load(f)

    if index < 0 or index >= len(restaurants):
        raise IndexError("Index không hợp lệ.")

    selected = restaurants[index]
    return {
        "name": selected.get("Name", selected.get("Address", "Không rõ tên")),
        "address": selected.get("Address", ""),
        "coordinates": selected.get("Coordinates", []),
        "route": selected.get("Route", []),
    }

def create_dummy_data():
    """Tạo file restaurants.json mẫu để test"""
    dummy_data = [
        {
            "Name": "Phở Hòa Pasteur",
            "Address": "260C Pasteur, Phường 8, Quận 3, Hồ Chí Minh"
        },
        {
            "Name": "Landmark 81",
            "Address": "720A Điện Biên Phủ, Bình Thạnh, Hồ Chí Minh"
        }
    ]
    with open("restaurants.json", "w", encoding="utf-8") as f:
        json.dump(dummy_data, f, ensure_ascii=False, indent=4)
    print("Đã tạo file 'restaurants.json' mẫu.")

def main():
    print("--- BẮT ĐẦU TEST ROUTING MODULE ---")
    
    # 1. Giả lập vị trí người dùng (Ví dụ: Chợ Bến Thành)
    user_lat = 10.7721
    user_lon = 106.6983
    print(f"Vị trí người dùng giả lập: {user_lat}, {user_lon}")

    # 2. Test hàm Geocode (Chuyển địa chỉ thành tọa độ)
    test_address = "Nhà Hát Thành Phố Hồ Chí Minh"
    print(f"\nĐang test Geocode địa chỉ: '{test_address}'...")
    try:
        lat, lon = geocode_address(test_address)
        print(f"--> Kết quả: Lat={lat}, Lon={lon}")
    except Exception as e:
        print(f"Lỗi Geocode: {e}")
        return # Dừng nếu lỗi ngay bước đầu

    # 3. Test hàm Routing (Tìm đường từ User -> Nhà Hát)
    print(f"\nĐang test tìm đường từ User đến '{test_address}'...")
    try:
        route_geometry = get_route(user_lat, user_lon, lat, lon)
        print(f"--> Thành công! Nhận được {len(route_geometry)} điểm tọa độ đường đi.")
    except Exception as e:
        print(f"Lỗi Routing: {e}")

    # 4. Test luồng xử lý toàn bộ (Preprocess)
    print("\nĐang chạy quy trình xử lý danh sách nhà hàng (Preprocess)...")
    create_dummy_data() # Tạo file input giả
    
    try:
        preprocess_restaurants(user_lat, user_lon)
        print("   -> Preprocess hoàn tất.")
    except Exception as e:
        print(f"Lỗi Preprocess: {e}")
        return

    # 5. Test đọc dữ liệu ra (Get Route)
    print("\nĐang thử đọc dữ liệu đã xử lý (Index 0)...")
    try:
        result = get_routes_from_json(0)
        print("   -> Kết quả đọc được:")
        print(f"      - Tên: {result['name']}")
        print(f"      - Địa chỉ: {result['address']}")
        print(f"      - Tọa độ quán: {result['coordinates']}")
        print(f"      - Số điểm trên đường đi: {len(result['route'])}")
    except Exception as e:
        print(f"Lỗi đọc file JSON: {e}")

    print("\n--- KẾT THÚC TEST ---")

if __name__ == "__main__":
    main()