import os
# Tắt oneDNN optimizations của TensorFlow để tránh xung đột (nếu có dùng thư viện liên quan)
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import json
import sqlite3
import math
import requests  
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai

# --- 1. CẤU HÌNH VÀ TẢI DỮ LIỆU TOÀN CỤC ---

# Tải biến môi trường từ file .env
load_dotenv()
GOOGLE_API = os.getenv("GOOGLE_API")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API")

# Cấu hình Gemini AI
if GOOGLE_API:
    genai.configure(api_key=GOOGLE_API)
else:
    print("Error: GOOGLE_API_KEY not found. Please check your .env file.")
    # Trong môi trường production, có thể không muốn exit ngay, nhưng giữ nguyên logic cũ
    # exit() 

if not GEOAPIFY_API_KEY:
    print("Error: GEOAPIFY_API_KEY not found. Please check your .env file.")
    # exit()

# Định nghĩa các luật ăn kiêng (Dùng cho context của Gemini)
DIET_RULES = {
    "vegan": {
        "allowed": ["vegetables", "fruits", "grains", "legumes", "nuts", "seeds", "tofu", "plant oils"],
        "prohibited": ["meat", "poultry", "fish", "seafood", "dairy", "eggs", "honey", "animal gelatin",
                       "fish sauce (nước mắm)"],
        "description": "Strict plant-based diet. No animal products whatsoever."
    },
    "vegetarian": {
        "allowed": ["vegetables", "fruits", "grains", "legumes", "dairy", "eggs", "honey"],
        "prohibited": ["meat", "poultry", "fish", "seafood", "animal gelatin", "traditional fish sauce"],
        "description": "No meat or seafood. Dairy and eggs are usually okay (Lacto-Ovo)."
    },
    "halal": {
        "allowed": ["halal meat (beef, lamb, chicken)", "fish", "seafood", "vegetables", "fruit", "grains"],
        "prohibited": ["pork (heo)", "lard", "blood", "alcohol (rượu/bia)",
                       "meat not slaughtered according to islamic rites"],
        "description": "Islamic dietary laws. STRICTLY NO PORK or ALCOHOL."
    },
    "hindu": {
        "allowed": ["vegetables", "dairy", "grains", "chicken (some)", "lamb (some)", "fish (some)"],
        "prohibited": ["beef (bò)", "pork (often avoided)", "alcohol (often avoided)"],
        "description": "Hindu dietary customs. STRICTLY NO BEEF. Many Hindus are also vegetarian."
    },
    "kosher": {
        "allowed": ["kosher meat (beef, lamb, poultry)", "fish with scales"],
        "prohibited": ["pork", "shellfish (shrimp, crab, lobster)", "mixing meat and dairy"],
        "description": "Jewish dietary laws. No pork or shellfish. Never mix meat and milk."
    }
}

# --- 2. CÁC HÀM HỖ TRỢ (HELPER FUNCTIONS) ---

def haversine(lat1, lon1, lat2, lon2):
    """
    Tính khoảng cách đường tròn lớn (great circle distance) giữa hai điểm 
    trên trái đất (tính bằng độ thập phân).
    """
    # Chuyển đổi độ thập phân sang radian
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # Công thức haversine
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Bán kính trái đất tính bằng km
    return c * r


def get_coords_for_location(location_name):
    """
    Sử dụng Geoapify để lấy tọa độ từ tên địa điểm (ví dụ: "District 1")
    """
    # Ưu tiên kết quả tìm kiếm tại TP. Hồ Chí Minh
    HCMC_LON = 106.660172
    HCMC_LAT = 10.762622

    try:
        url = "https://api.geoapify.com/v1/geocode/search"
        params = {
            'text': f"{location_name}, Ho Chi Minh City",
            'apiKey': GEOAPIFY_API_KEY,
            'limit': 1,
            'bias': f'proximity:{HCMC_LON},{HCMC_LAT}'
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data['features']:
            geometry = data['features'][0]['geometry']
            if geometry['type'] == 'Point':
                lon, lat = geometry['coordinates']
                return lat, lon
        return None, None

    except Exception as e:
        print(f"Error geocoding user location: {e}")
        return None, None


def get_bounding_box(lat, lon, distance_km):
    """
    Tạo một khung bao (bounding box) hình vuông quanh một điểm.
    1 độ vĩ độ ~ 111km.
    """
    lat_change = distance_km / 111.0
    # Thay đổi kinh độ phụ thuộc vào vĩ độ (nhân tố cos)
    lon_change = distance_km / (111.0 * math.cos(math.radians(lat)))

    return {
        "min_lat": lat - lat_change,
        "max_lat": lat + lat_change,
        "min_lon": lon - lon_change,
        "max_lon": lon + lon_change
    }


# --- 3. CÁC HÀM XỬ LÝ NHIỆM VỤ (MISSION HANDLERS) ---

def handle_culture_query(prompt):
    print("-> Executing: Culture Query")
    system_context = (
        "You are a Vietnamese cultural expert. Answer clearly. "
        "If the topic involves food taboos (e.g. Pork in Islam), explicitly mention them."
    )
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content([system_context, prompt])
    return response.text


def route_user_request(prompt):
    """
    Phân loại ý định người dùng và trích xuất thực thể.
    """
    system_context = (
        "You are a travel assistant. Classify intent into: 'culture_query', 'food_recommendation', 'restaurant_recommendation', 'daily_menu'.\n"
        "Extract entities:\n"
        "- 'location': specific area (e.g., 'District 1')\n"
        "- 'cuisine': specific dish (e.g., 'Pho')\n"
        "- 'diet_ingredient': restrictions (e.g., 'vegan', 'halal')\n"
        "- 'budget': price preference (e.g., 'cheap', 'street food', 'luxury', 'under 50k'). Default 'none'."
    )

    schema = {
        "type": "OBJECT",
        "properties": {
            "task": {"type": "STRING"},
            "location": {"type": "STRING"},
            "cuisine": {"type": "STRING"},
            "diet_ingredient": {"type": "STRING"},
            "budget": {"type": "STRING"}
        },
        "required": ["task"]
    }

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(
        [system_context, "User prompt: " + prompt],
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": schema
        }
    )

    try:
        return json.loads(response.text)
    except Exception as e:
        print(f"Error parsing router response: {e}")
        return {"task": "unknown"}


def handle_restaurant_recommendation(prompt, entities):
    location = entities.get('location')
    cuisine = entities.get('cuisine')
    budget = entities.get('budget','any')

    print(f"-> Executing: Restaurant Recommendation (Location: {location}, Cuisine: {cuisine})")

    user_lat, user_lon = None, None
    if location and location.lower() != 'none':
        user_lat, user_lon = get_coords_for_location(location)

    # Kết nối Database
    conn = sqlite3.connect('foody_data.sqlite')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM Restaurants"
    params = []
    conditions = []

    # Lọc theo vị trí (Bounding Box) nếu có tọa độ
    if user_lat and user_lon:
        bbox = get_bounding_box(user_lat, user_lon, distance_km=10)
        conditions.append("Latitude BETWEEN ? AND ?")
        conditions.append("Longitude BETWEEN ? AND ?")
        params.extend([bbox['min_lat'], bbox['max_lat'], bbox['min_lon'], bbox['max_lon']])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Xử lý & Lọc kết quả
    results = []
    search_term = cuisine.lower() if cuisine and cuisine != 'none' else ""

    for row in rows:
        rest = dict(row)
        rest_name = str(rest['Name']).lower()

        # Lọc cơ bản theo tên món ăn/cuisine
        if search_term and search_term not in rest_name:
            continue

        try:
            rest['Rating'] = float(rest['Rating'])
        except (ValueError, TypeError):
            rest['Rating'] = 0.0

        if user_lat and user_lon:
            try:
                r_lat = float(rest['Latitude'])
                r_lon = float(rest['Longitude'])
                dist = haversine(user_lat, user_lon, r_lat, r_lon)
                rest['distance_km'] = round(dist, 2)
            except (ValueError, TypeError):
                rest['distance_km'] = 9999
        else:
            rest['distance_km'] = 0

        results.append(rest)

    model = genai.GenerativeModel('gemini-2.5-flash')

    # --- FALLBACK LOGIC ---
    if not results:
        print("-> No matches in DB. Switching to Cultural Fallback.")
        fallback_system_context = (
             f"User asked for '{cuisine}' near '{location}' (Budget: {budget}). No DB matches.\n"
            "1. Politely apologize for missing data.\n"
            "2. Provide general cultural info about the dish.\n"
            "3. **Estimate the typical price** for this dish in Vietnam (e.g. 'Usually 30k-50k')."
        )
        response = model.generate_content([fallback_system_context, f"User Query: {prompt}"])
        # Trả về text giải thích, danh sách nhà hàng rỗng
        return {
            "text": response.text,
            "restaurants": []
        }
    # --- END FALLBACK ---

    # Xếp hạng: Ưu tiên Rating cao, sau đó đến khoảng cách gần
    results.sort(key=lambda x: (-x['Rating'], x['distance_km']))
    top_results = results[:50]

    # Gửi kết quả từ Database cho Gemini để format
    restaurant_context = json.dumps(top_results, ensure_ascii=False)

    system_context = (
        "You are a local restaurant guide. Your job is to recommend 3-5 top restaurants to the user. "
        "Use the provided JSON database. "
        "The JSON includes an 'img' field containing an image path. For example 'foody_images/img_name.jpg' "
        "The JSON includes a 'distance_km' field showing how far the restaurant is from the user. "
        "Mention this distance in your answer. "
        "For EACH restaurant, based on its name/type (e.g. 'Cơm Tấm' vs 'Nhà Hàng'), provide an **Estimated Cost** range in VND.\n"
        "- Street Food/Bình Dân: ~30k - 60k VND\n"
        "- Mid-range: ~80k - 150k VND\n"
        "- High-end: >200k VND\n"
        "Check if the estimated cost matches the User's Budget. If not, mention it (e.g. 'This is a bit pricier than your request').\n\n"
        "Always respond in the same language that the user used in their query.\n"
        f"USER LOCATION: {location}\n"
        f"USER CUISINE: {cuisine}\n"
        f"USER BUDGET: {budget}\n"
        f"DATABASE:\n{restaurant_context}"
    )

    schema = {
        "type": "OBJECT",
        "properties": {
            "explanation": {"type": "STRING"},
            "recommendations": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "Name": {"type": "STRING"},
                        "Address": {"type": "STRING"},
                        "Rating": {"type": "NUMBER"},
                        "Budget": {"type":"NUMBER"},
                        "distance_km": {"type": "NUMBER"},
                        "Description": {"type": "STRING"}, 
                        "img": {"type": "STRING"}
                    },
                    "required": ["Name"]
                }
            }
        },
        "required": ["recommendations"]
    }

    response = model.generate_content(
        [system_context, prompt],
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": schema
        }
    )

    try:
        result = json.loads(response.text)
        return {
            "text": result.get("explanation", ""),
            "restaurants": result.get("recommendations", [])
        }
    except json.JSONDecodeError:
        return {
            "text": "Error parsing AI response.",
            "restaurants": []
        }


def handle_food_recommendation(prompt, entities):
    """
    Nhiệm vụ 2: Gợi ý món ăn (RAG hoặc kiến thức chung)
    """
    diet = entities.get('diet_ingredient','General')
    budget = entities.get('budget','any')
    print(f"-> Executing: Food Recommendation (Diet: {diet})")

    system_context = (
        f"User wants a food suggestion. Request: {prompt}\n"
        f"Diet: {diet}. Budget: {budget}.\n"
        "--------------------------------------------------\n"
        "1. Recommend 3 authentic Vietnamese dishes.\n"
        "2. **Safety Check:** Explain WHY it fits the diet (e.g. 'Safe for Halal because...').\n"
        "3. **Cost Estimation:** Provide a typical price range for this dish (Street vs Restaurant price).\n"
        "4. **Nutrient Detail:** Est. Calories/Protein/Carbs/Fat."
    )

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content([system_context, "User Request: " + prompt])
    return response.text


def handle_daily_menu(prompt, entities):
    budget = entities.get('budget', 'any')
    print(f"-> Daily Menu: Budget {budget}")

    model = genai.GenerativeModel('gemini-2.5-flash')

    sys_msg = (
        f"Create a 1-Day Vietnamese Meal Plan (Breakfast, Lunch, Dinner).\n"
        f"Budget Level: {budget}.\n"
        "1. Suggest specific dishes.\n"
        "2. **Total Cost:** Estimate the total daily cost in VND based on the budget level.\n"
        "3. **Nutrients:** Calculate approx total calories/protein for the day."
    )
    return model.generate_content([sys_msg, prompt]).text


# --- 4. VÒNG LẶP CHÍNH VÀ API ---

def replyToUser(data):
    """
    Hàm API chính để giao tiếp với frontend/backend khác.
    Output format: {"reply": string, "food_data": list}
    """
    message_text = data.get('message', '').strip()

    if not message_text:
        return {"reply": "Xin vui lòng nhập câu hỏi.", "food_data": []}

    try:
        task_data = route_user_request(message_text)
        task_type = task_data.get('task', 'unknown')

        if task_type == 'culture_query':
            reply_text = handle_culture_query(message_text)
            food_data = []

        elif task_type == 'food_recommendation':
            reply_text = handle_food_recommendation(message_text, task_data)
            food_data = []

        elif task_type == 'restaurant_recommendation':
            result = handle_restaurant_recommendation(message_text, task_data)
            # result có thể là dict từ handle_restaurant_recommendation hoặc text từ fallback
            if isinstance(result, dict):
                reply_text = result.get("text", "")
                food_data = result.get("restaurants", [])
            else:
                # Trường hợp fallback trả về string thuần (nếu có lỗi logic cũ, giữ an toàn)
                reply_text = str(result)
                food_data = []

        elif task_type == 'daily_menu':
            reply_text = handle_daily_menu(message_text, task_data)
            food_data = []
            
        else:
            reply_text = "Xin lỗi, tôi chưa hiểu yêu cầu của bạn."
            food_data = []

        return {
            "reply": reply_text,
            "food_data": food_data
        }

    except Exception as e:
        print("Error in replyToUser:", e)
        return {
            "reply": "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau.",
            "food_data": []
        }

# --- MAIN BLOCK CHO TESTING ---
if __name__ == "__main__":
    print("\n--- 🤖 Welcome to the Vietnam Cultural & Food Consultant ---")
    while True:
        prompt = input("You: ")
        if prompt.lower() in ['exit', 'quit']:
            break
        
        # Giả lập data input từ frontend
        response_data = replyToUser({"message": prompt})
        
        print(f"\nGemini: {response_data['reply']}")
        if response_data['food_data']:
            print(f"[Debug] Restaurants found: {len(response_data['food_data'])}")
            for r in response_data['food_data'][:2]: # Print mẫu 2 cái
                print(f" - {r.get('Name')} ({r.get('distance_km')} km)")
        print("-" * 50)