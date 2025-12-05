
import os
os.environ["GRPC_VERBOSITY"] = "NONE"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import requests
from requests.structures import CaseInsensitiveDict
import google.generativeai as genai
import google.ai.generativelanguage as glm
from flask import jsonify

import json
import csv

from dotenv import load_dotenv

load_dotenv()
GEOAPIFY_API = os.getenv("GEOAPIFY_API")
GOOGLE_API = os.getenv("GOOGLE_API")
Quantity = 5

genai.configure(api_key=GOOGLE_API)

def geminiNLP(prompt):
    with open("RestaurantFormat.txt", "r", encoding="utf-8") as f:
        cat_file = f.read()

    system_context = (
        "Bạn là bộ lọc và ánh xạ category.\n"
        "Dưới đây là toàn bộ danh sách category chuẩn:\n"
        f"{cat_file}\n"
        "Nhiệm vụ: Từ prompt người dùng, hãy xác định categories và location. "
        "Sau đó ánh xạ mỗi category sang danh sách chuẩn trên."
    )

    schema = glm.Schema(
        type = glm.Type.ARRAY,
        items = glm.Schema(
            type = glm.Type.OBJECT,
            properties = {
                "Categories": glm.Schema(type = glm.Type.STRING),
                "Location": glm.Schema(type = glm.Type.STRING),
                "Mapped": glm.Schema(type = glm.Type.STRING),
            },
            required = ["Categories", "Location", "Mapped"]
        )
    )

    model = genai.GenerativeModel('gemini-2.5-flash')

    response = model.generate_content(
        [system_context, "User prompt: " + prompt],
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": schema
        }
    )
    try:
        data = json.loads(response.text)  
        return data
    except json.JSONDecodeError:
        print("Lỗi: response không phải JSON hợp lệ")
        return None
    
def bboxForLocation(location = "Quận 7, TP.HCM"):
    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q":location,
        "polygon_geojson":1,
        "format":"json"
    }
    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/json"
    headers["User-Agent"] = "Mozilla/5.0 (compatible; myapp/1.0; +https://example.com)"
    resp = requests.get(url,params = params, headers=headers)

    data = resp.json()[0]["boundingbox"]

    south = float(data[0])
    north = float(data[1])
    west  = float(data[2])
    east  = float(data[3]) 
    
    bbox = f"{west},{south},{east},{north}"
    return bbox


def restaurantForLocation(bbox, Categories = "catering", keyword=None):
    base_url = "https://api.geoapify.com/v2/places"

    params = {
        "apiKey": GEOAPIFY_API,
        "limit": Quantity,
        "filter": f"rect:{bbox}",
    }

   
    if Categories:
        params["categories"] = Categories

   
    if keyword:
        params["text"] = keyword

    resp = requests.get(base_url, params=params)
    return resp.json()

def writeCSV(RestaurantList):
    with open("Restaurant.csv", "w",newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file,fieldnames = ["Name","Address","OpeningTime","Cuisine"])
        writer.writeheader()
        for i in RestaurantList:
            writer.writerow(i)

def writeJSON(RestaurantList):
    with open("Restaurant.json", "w", encoding="utf-8") as file:
        json.dump(RestaurantList, file, ensure_ascii=False, indent=4)

def restaurantSuggest(prompt):
    dictionary = geminiNLP(prompt)

    bbox = bboxForLocation(dictionary[0]["Location"])
    data = restaurantForLocation(bbox,dictionary[0]["Mapped"],dictionary[0]["Categories"])

    RestaurantList = []

    for i in data["features"]:
        props = i["properties"]

        if "catering" in props and "cuisine" in props["catering"]:
            cuisine = props["catering"]["cuisine"]
        elif "datasource" in props and "raw" in props["datasource"] and "cuisine" in props["datasource"]["raw"]:
            cuisine = props["datasource"]["raw"]["cuisine"]
        else:
            cuisine = None

        RestaurantList.append({
            "Name": props.get("name"),
            "Address": props.get("address_line2"),
            "OpeningTime": props.get("opening_hours"),
            "Cuisine": cuisine
        })
    return RestaurantList

def replyToUser(data):
    try:
        # 1. Nhận dữ liệu JSON từ request
        user_message = data.get('message')

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # 2. Gọi hàm logic từ SearchModule
        restaurant_list = restaurantSuggest(user_message)

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
def main():

    prompt = input("Enter a prompt: ")
    dictionary = geminiNLP(prompt)

    bbox = bboxForLocation(dictionary[0]["Location"])
    data = restaurantForLocation(bbox,dictionary[0]["Mapped"],dictionary[0]["Categories"])

    RestaurantList = []

    for i in data["features"]:
        props = i["properties"]

        if "catering" in props and "cuisine" in props["catering"]:
            cuisine = props["catering"]["cuisine"]
        elif "datasource" in props and "raw" in props["datasource"] and "cuisine" in props["datasource"]["raw"]:
            cuisine = props["datasource"]["raw"]["cuisine"]
        else:
            cuisine = None

        RestaurantList.append({
            "Name": props.get("name"),
            "Address": props.get("address_line2"),
            "OpeningTime": props.get("opening_hours"),
            "Cuisine": cuisine
        })

    for i in RestaurantList:
        print(f"Name: {i['Name']}")
        print(f"Address: {i['Address']}")
        print(f"OpeningTime: {i['OpeningTime']}")
        print(f"Cuisine: {i['Cuisine']}")
        print()

    # writeJSON(RestaurantList)
    # writeCSV(RestaurantList)

if __name__ == "__main__":
    main()