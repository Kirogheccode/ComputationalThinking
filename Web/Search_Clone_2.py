import os
import json
import math
import sqlite3
import requests
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

# ============================================================
# 1. LOAD CONFIG
# ============================================================

load_dotenv()
GOOGLE_API = os.getenv("GOOGLE_API")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API")

if GOOGLE_API:
    genai.configure(api_key=GOOGLE_API)
else:
    print("❌ Missing GOOGLE_API_KEY")
    exit()

if not GEOAPIFY_API_KEY:
    print("❌ Missing GEOAPIFY_API_KEY")
    exit()


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def haversine(lat1, lon1, lat2, lon2):
    try:
        lon1, lat1, lon2, lat2 = map(math.radians, [float(lon1), float(lat1), float(lon2), float(lat2)])
        a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        return 6371 * 2 * math.asin(math.sqrt(a))
    except:
        return 0


def get_coords_for_location(location_name):
    try:
        url = "https://api.geoapify.com/v1/geocode/search"
        params = {
            "text": f"{location_name}, Ho Chi Minh City",
            "apiKey": GEOAPIFY_API_KEY,
            "limit": 1,
            "bias": "proximity:106.660172,10.762622"
        }
        res = requests.get(url, params=params)
        js = res.json()
        if js["features"]:
            coords = js["features"][0]["geometry"]["coordinates"]
            return coords[1], coords[0]
    except:
        return None, None
    return None, None


def get_bounding_box(lat, lon, km):
    lat_change = km / 111.0
    lon_change = km / (111.0 * math.cos(math.radians(lat)))
    return {
        "min_lat": lat - lat_change,
        "max_lat": lat + lat_change,
        "min_lon": lon - lon_change,
        "max_lon": lon + lon_change
    }


def is_open_now(hours_str):
    if not hours_str or hours_str.lower() == "updating":
        return True
    try:
        now = datetime.now().time()
        s, e = hours_str.split(" - ")
        t1 = datetime.strptime(s.strip(), "%H:%M").time()
        t2 = datetime.strptime(e.strip(), "%H:%M").time()
        if t1 < t2:
            return t1 <= now <= t2
        return now >= t1 or now <= t2
    except:
        return True


# ============================================================
# 3. ROUTER (y như App.py)
# ============================================================

def route_user_request(prompt):
    prompt_lower = prompt.lower()

    # các lệnh nhanh
    if prompt_lower.startswith("/eat"):
        return {"task": "restaurant_recommendation", "cuisine": prompt.replace("/eat", "").strip(), "location": "none"}
    if prompt_lower.startswith("/cook"):
        return {"task": "food_recommendation", "cuisine": prompt.replace("/cook", "").strip()}
    if prompt_lower.startswith("/plan"):
        return {"task": "daily_menu"}

    # AI classification dùng JSON schema
    model = genai.GenerativeModel("gemini-2.5-flash")

    sys_msg = (
        "Classify intent: 'culture_query', 'food_recommendation', "
        "'restaurant_recommendation', 'daily_menu'.\n"
        "Extract: location, cuisine, diet_ingredient, category."
    )

    schema = {
        "type": "OBJECT",
        "properties": {
            "task": {"type": "STRING"},
            "location": {"type": "STRING"},
            "cuisine": {"type": "STRING"},
            "diet_ingredient": {"type": "STRING"},
            "category": {"type": "STRING"}
        },
        "required": ["task"]
    }

    try:
        res = model.generate_content(
            [sys_msg, prompt],
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": schema
            }
        )
        return json.loads(res.text)
    except:
        return {"task": "unknown"}


# ============================================================
# 4. MAIN: RESTAURANT RECOMMENDER (y hệt App.py)
# ============================================================

def handle_restaurant_recommendation(prompt, entities):
    loc = entities.get("location")
    cuisine = entities.get("cuisine")
    category = entities.get("category", "").lower()

    # --- Geocode
    user_lat, user_lon = None, None
    if loc and loc != "none":
        user_lat, user_lon = get_coords_for_location(loc)

    # --- SQL
    conn = sqlite3.connect("data/foody_data.sqlite")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = "SELECT * FROM Restaurants"
    params = []

    if user_lat:
        bbox = get_bounding_box(user_lat, user_lon, 10)
        query += " WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?"
        params = [bbox["min_lat"], bbox["max_lat"], bbox["min_lon"], bbox["max_lon"]]

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    results = []
    search_term = cuisine.lower() if cuisine and cuisine != "none" else ""

    for r in rows:
        item = dict(r)

        # A. Filter cuisine
        if search_term and search_term not in item["name"].lower():
            continue

        # B. Opening hours
        if not is_open_now(item["opening_hours"]):
            continue

        # C. Tags
        tags = str(item["tags"]).lower()
        if category and category not in tags:
            continue

        # D. Rating
        try:
            item["rating"] = float(item["rating"])
        except:
            item["rating"] = 0.0

        # E. Distance
        if user_lat:
            item["dist"] = round(haversine(user_lat, user_lon, item["latitude"], item["longitude"]), 2)
        else:
            item["dist"] = 0

        results.append(item)

    if not results:
        model = genai.GenerativeModel("gemini-2.5-flash")
        text = model.generate_content(
            f"No open restaurants for '{cuisine}' near '{loc}'. Suggest alternatives."
        ).text
        return {"reply": text, "restaurants": []}

    # Ranking
    results.sort(key=lambda x: (-x["rating"], x["dist"]))
    top = results[:5]

    # Format bằng Gemini
    model = genai.GenerativeModel("gemini-2.5-flash")
    sys_msg = (
        "Recommend 3–5 restaurants from the JSON list.\n"
        "Mention distance and say they are OPEN NOW.\n"
        f"List:\n{json.dumps(top, ensure_ascii=False)}"
    )
    text = model.generate_content([sys_msg, prompt]).text

    return {"reply": text, "restaurants": top}


# ============================================================
# 5. API PUBLIC
# ============================================================

def replyToUser(data):
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return {"reply": "Bạn chưa nhập câu hỏi.", "restaurants": []}

    entities = route_user_request(user_msg)
    task = entities.get("task")

    if task == "restaurant_recommendation":
        return handle_restaurant_recommendation(user_msg, entities)

    return {"reply": "Tính năng này chưa được hỗ trợ trong Search_Clone mới.", "restaurants": []}


# ============================================================
# 6. TEST CLI
# ============================================================

if __name__ == "__main__":
    print("=== Search_Clone.py (New) ===")
    while True:
        q = input("You: ")
        if q.lower() == "exit":
            break
        print(replyToUser({"message": q}))
