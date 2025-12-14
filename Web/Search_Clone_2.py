import os
import json
import sqlite3
import math
import requests
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

from SaveAnswer import saveAnswerForUser

# --- 1. CONFIGURATION ---

load_dotenv()
GOOGLE_API = os.getenv("GOOGLE_API_KEY")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")

if GOOGLE_API:
    genai.configure(api_key=GOOGLE_API)
else:
    print("Error: GOOGLE_API_KEY not found.")
    exit()

if not GEOAPIFY_API_KEY:
    print("Error: GEOAPIFY_API_KEY not found.")
    exit()

if not SPOONACULAR_API_KEY:
    print("Error: SPOONACULAR_API_KEY not found.")
    exit()

# --- DIET KNOWLEDGE BASE ---
DIET_RULES = {
    "vegan": {
        "allowed": ["vegetables", "fruits", "grains", "legumes", "nuts", "seeds", "tofu", "plant oils"],
        "prohibited": ["meat", "poultry", "fish", "seafood", "dairy", "eggs", "honey", "animal gelatin", "fish sauce (nước mắm)"],
        "description": "Strict plant-based diet. No animal products whatsoever."
    },
    "vegetarian": {
        "allowed": ["vegetables", "fruits", "grains", "legumes", "dairy", "eggs", "honey"],
        "prohibited": ["meat", "poultry", "fish", "seafood", "animal gelatin", "traditional fish sauce"],
        "description": "No meat or seafood. Dairy and eggs are usually okay (Lacto-Ovo)."
    },
    "halal": {
        "allowed": ["halal meat (beef, lamb, chicken)", "fish", "seafood", "vegetables", "fruit", "grains"],
        "prohibited": ["pork (heo)", "lard", "blood", "alcohol (rượu/bia)", "meat not slaughtered according to islamic rites"],
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

# --- 2. HELPER FUNCTIONS ---

def get_nutrition_from_spoonacular(dish_name):
    """
    Searches Spoonacular for a specific dish and returns its nutrition string.
    """

    # We use 'complexSearch' to find the closest matching recipe and get its stats
    url = "https://api.spoonacular.com/recipes/complexSearch"
    params = {
        "apiKey": SPOONACULAR_API_KEY,
        "query": dish_name,
        "number": 1,
        "addRecipeNutrition": "true"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if data['results']:
            # Extract the first matching recipe
            item = data['results'][0]
            nutrients = item.get('nutrition', {}).get('nutrients', [])

            # Helper to find a specific nutrient in the list
            def find_n(name):
                for n in nutrients:
                    if n['name'] == name: 
                        return f"{n['amount']}" + " " + f"{n['unit']}"
                return "?"
            
            return {
                "Calories": find_n("Calories"),
                "Protein": find_n("Protein"),
                "Fat": find_n("Fat")
            }
    except Exception as e:
        print(f"Spoonacular Error for {dish_name}: {e}")
        return {}


def haversine(lat1, lon1, lat2, lon2):
    try:
        lon1, lat1, lon2, lat2 = map(math.radians, [float(lon1), float(lat1), float(lon2), float(lat2)])
        a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        return 6371 * 2 * math.asin(math.sqrt(a))
    except (ValueError, TypeError):
        return 0


def get_coords_for_location(location_name):
    try:
        url = "https://api.geoapify.com/v1/geocode/search"
        params = {
            'text': f"{location_name}, Ho Chi Minh City",
            'apiKey': GEOAPIFY_API_KEY,
            'limit': 1,
            'bias': 'proximity:106.660172,10.762622'
        }
        resp = requests.get(url, params=params)
        if resp.ok and resp.json()['features']:
            coords = resp.json()['features'][0]['geometry']['coordinates']
            return coords[1], coords[0]  # Lat, Lon
    except Exception as e:
        print(f"Geocoding error: {e}")
    return None, None


def get_bounding_box(lat, lon, km):
    lat_change = km / 111.0
    lon_change = km / (111.0 * math.cos(math.radians(lat)))
    return {
        "min_lat": lat - lat_change, "max_lat": lat + lat_change,
        "min_lon": lon - lon_change, "max_lon": lon + lon_change
    }


def is_open_now(hours_str):
    """
    Parses '09:00 - 22:00' and checks against current system time.
    Returns True if Open, False if Closed.
    """
    if not hours_str or hours_str.lower() == 'updating' or not '-' in hours_str:
        return True  # Default to Open if unknown

    try:
        now = datetime.now().time()
        start_str, end_str = hours_str.split(' - ')
        start_time = datetime.strptime(start_str.strip(), "%H:%M").time()
        end_time = datetime.strptime(end_str.strip(), "%H:%M").time()

        if start_time < end_time:
            # Normal range (e.g., 09:00 - 22:00)
            return start_time <= now <= end_time
        else:
            # Cross-midnight range (e.g., 16:00 - 02:00)
            return now >= start_time or now <= end_time
    except:
        return True  # Default to True on parse error


# --- 3. MISSION HANDLERS ---

def handle_culture_query(prompt):
    print("-> Executing: Culture Query")
    model = genai.GenerativeModel('gemini-2.5-flash')
    sys_msg = "You are a Vietnamese cultural expert. Answer clearly in English. If the topic involves food taboos (e.g. Pork in Islam), explicitly mention them."
    return model.generate_content([sys_msg, prompt]).text


def route_user_request(prompt):

    # Có thể viết thêm context prompt để lọc chuẩn hơn
    schema = {
        "type": "OBJECT",
        "properties": {
            "location": {"type": "STRING"},
            "cuisine": {"type": "STRING"},
            "budget": {"type": "STRING"},
            "diet_ingredient": {"type": "STRING"}
        },
    }

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(
        ["User prompt: " + prompt],
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
    budget = entities.get('budget','')

    print(f"-> Executing: Restaurant Recommendation (Location: {location}, Cuisine: {cuisine})")

    user_lat, user_lon = None, None
    if location and location.lower() != 'none':
        user_lat, user_lon = get_coords_for_location(location)

    conn = sqlite3.connect('data/foody_data.sqlite')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM Restaurants"
    params = []
    conditions = []

    if user_lat and user_lon:
        bbox = get_bounding_box(user_lat, user_lon, km=10)
        conditions.append("Latitude BETWEEN ? AND ?")
        conditions.append("Longitude BETWEEN ? AND ?")
        params.extend([bbox['min_lat'], bbox['max_lat'], bbox['min_lon'], bbox['max_lon']])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # 3. Process & Filter
    results = []
    search_term = cuisine.lower() if cuisine else ""

    for row in rows:
        rest = dict(row)
        rest_name = str(rest['name']).lower()

        if search_term and search_term not in rest_name:
            continue

        try:
            rest['rating'] = float(rest['rating'])
        except (ValueError, TypeError):
            rest['rating'] = 0.0

        if user_lat and user_lon:
            try:
                r_lat = float(rest['latitude'])
                r_lon = float(rest['longitude'])
                dist = haversine(user_lat, user_lon, r_lat, r_lon)
                rest['distance_km'] = round(dist, 2)
            except (ValueError, TypeError):
                rest['distance_km'] = 9999
        else:
            rest['distance_km'] = 0

        results.append(rest)

    # --- FALLBACK LOGIC STARTS HERE ---
    model = genai.GenerativeModel('gemini-2.5-flash')

    if not results:
        print("-> No matches in DB. Switching to Cultural Fallback.")
        fallback_system_context = (
            "You are a knowledgeable local guide for Vietnam. "
            "The user asked for a specific restaurant or dish in a specific location, but your local database returned ZERO matches. "
            "1. First, politely inform the user that you don't have specific restaurant data for that request in your current database. "
            "2. Then, pivot to providing helpful **General/Cultural Knowledge** about the food they asked for. "
            "Describe what the dish is, its history, or general tips on where to find it in Vietnam (e.g., 'You can usually find this dish in street stalls...')."
        )
        response = model.generate_content([fallback_system_context, f"User Query: {prompt}"])
        return response.text
    # --- FALLBACK LOGIC ENDS HERE ---

    # 4. Rank
    results.sort(key=lambda x: (-x['rating'], x['distance_km']))
    top_results = results[:50]

    # 5. Send Database Results to Gemini
    restaurant_context = json.dumps(top_results, ensure_ascii=False)

    system_context = (
        "You are a local restaurant guide. Your job is to recommend 3-5 top restaurants to the user. "
        "Use the provided JSON database. "
        "The JSON includes an 'img' field containing an image path. For example 'foody_images/img_name.jpg' "
        "The JSON includes a 'distance_km' field showing how far the restaurant is from the user. "
        "Mention this distance in your answer. "
        "Always respond in the same language that the user used in their query."
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
                        "Budget": {"type":"STRING"},
                        "distance_km": {"type": "NUMBER"},
                        "Description": {"type": "STRING"},  # <--- THÊM Ở ĐÂY
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

    result = json.loads(response.text)

    return {
        "text": result.get("explanation", ""),
        "restaurants": result.get("recommendations", {})
    }



def handle_food_recommendation(prompt, entities):
    diet = entities.get('diet_ingredient', 'General')
    print(f"-> Food Rec (Direct LLM): {diet}")

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
                        "Description": {"type": "STRING"},
                        "AuthencityNote": {"type":"STRING"},
                        "FoodUnitToCalculateNutritions": {"type": "STRING"},
                        "DietaryCompatibility": {"type":"STRING"},
                        "Calories": {"type":"STRING"},
                        "Protein": {"type":"STRING"},
                        "Carbs": {"type":"STRING"},
                        "Fat": {"type":"STRING"}
                    },
                    "required": ["Name"]
                }
            }
        },
        "required": ["recommendations"]
    }

    model = genai.GenerativeModel('gemini-2.5-flash')
    sys_msg = (
        f"You are an expert Vietnamese culinary. User wants a dish suggestion. Diet: {diet}.\n"
        "1. Recommend 3 specific authentic Vietnamese dishes (english reply) or if users mention certain dishes, focus the answer on them.\n"
        f"2. Warn if dish conflicts with restrictions (e.g. Pork/Halal), based on {DIET_RULES}.\n"
        "3. Provide estimated Calories/Protein/Carbs/Fat and cost."
    )
    response = model.generate_content(
        [sys_msg, prompt],
        generation_config={
        "response_mime_type": "application/json",
        "response_schema": schema
    })

    result = json.loads(response.text)

    return {
        "text": result.get("explanation", ""),
        "restaurants": result.get("recommendations", {})
    }

def handle_daily_menu(prompt, entities):
    budget = entities.get('budget', 'moderate')
    diet = entities.get('diet_ingredient', '')

    print(f"-> Daily Menu (Hybrid): Diet={diet}, Budget={budget}")

    # --- STAGE 1: ASK GEMINI FOR DISH NAMES (Structured JSON) ---
    model = genai.GenerativeModel('gemini-2.5-flash')

    # We force Gemini to output JSON so we can read it easily in Python
    context = (
        f"Create a 1-Day Vietnamese Meal Plan (Breakfast, Lunch, Dinner) (english reply). Diet: {diet}.\n"
        "Return ONLY a valid JSON object with keys 'breakfast', 'lunch', 'dinner'.\n"
        "Value should be the Vietnamese dish name (e.g. 'Pho Bo'), avoid the options that users have to cook themselves.\n"
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
                        "MainMeal": {"type":"STRING"},
                        "FoodName": {"type": "STRING"},
                        "CulturalSignificance": {"type":"STRING"}
                    },
                    "required": ["FoodName", "MainMeal"]
                }
            }
        },
        "required": ["recommendations"]
    }
    try:
        # Get dish names
        response = model.generate_content(
            [context, prompt],
            generation_config={
            "response_mime_type": "application/json",
            "response_schema": schema
        })
        menu_plan = json.loads(response.text)
    except Exception as e:
        # Fallback if JSON fails
        print("Lỗi:",e)
        return {
            "text": "Hệ thống đang bận !",
            "menu": {}
        }
    # --- STAGE 2: FETCH NUTRITION FOR THESE DISHES ---

    print("   Fetching Spoonacular Data...")
    for meal in menu_plan["recommendations"]:
        stats = get_nutrition_from_spoonacular(meal["FoodName"])
        if stats:
            meal["Calories"] = stats["Calories"]
            meal["Protein"] = stats["Protein"]
            meal["Fat"] = stats["Fat"]
        else:
            meal["Calories"] = "Nutrition data unavailable"
            meal["Protein"] = "Nutrition data unavailable"
            meal["Fat"] = "Nutrition data unavailable"
    
    return {
        "text": menu_plan.get("explanation", ""),
        "menu": menu_plan.get("recommendations", {})
    }


def handle_daily_menu_fallback(prompt):
    # Simple backup if JSON parsing fails
    model = genai.GenerativeModel('gemini-2.5-flash')
    return model.generate_content(f"Create a Vietnamese meal plan for: {prompt}").text

# --- 4. MAIN ---

def main_chatbot():
    print("\n--- 🤖 Vietnam Food AI ---")
    #print("Filters enabled: Open Now, Distance, Tags (Student/Family/etc)")

    while True:
        prompt = input("You: ")
        if prompt.lower() in ['exit', 'quit']: break

        try:
            data = route_user_request(prompt)
            task = data.get('task')

            if task == 'culture_query':
                resp = handle_culture_query(prompt)
            elif task == 'food_recommendation':
                resp = handle_food_recommendation(prompt, data)
            elif task == 'restaurant_recommendation':
                resp = handle_restaurant_recommendation(prompt, data)
            elif task == 'daily_menu':
                resp = handle_daily_menu(prompt, data)
            else:
                resp = "I'm not sure how to help with that."

            print(f"\nGemini: {resp}\n")
        except Exception as e:
            print(f"Error: {e}")

# ============================================================
# 5. API PUBLIC
# ============================================================


def replyToUser(data,users = "users"):
    user_msg = data.get("message", "").strip()
    task = data.get("mode")

    # CASE 1: Empty Input
    if not user_msg:
        return {"reply": "Bạn chưa nhập câu hỏi.", "restaurants": []}

    entities = route_user_request(user_msg)
    food_data = []

    # Execute the logic and get the text string
    if task == "":
        reply_text = handle_culture_query(user_msg)
        saveAnswerForUser(reply_text,task,users)
    elif task == "/place_":
        response = handle_restaurant_recommendation(user_msg, entities)
        reply_text =  response["text"]
        food_data = response["restaurants"]
        saveAnswerForUser(food_data,task,users)
    elif task == '/recipe_':
        response = handle_food_recommendation(user_msg, entities)
        reply_text =  response["text"]
        food_data = response["restaurants"]
        saveAnswerForUser(food_data,task,users)
    elif task == '/plan_':
        response = handle_daily_menu(user_msg, entities)
        reply_text =  response["text"]
        food_data = response["menu"]
        saveAnswerForUser(food_data,task,users)
    else:
        reply_text = "I'm not sure how to help with that."
    
    # CASE 2: Valid Response
    # Wrap the text in a dictionary so app.py converts it to {"reply": "..."}
    return {
        "reply": reply_text,
        "food_data": food_data  # Add this if your frontend expects it to prevent errors
    }
if __name__ == "__main__":
    print("=== Search_Clone.py (New) ===")
    while True:
        q = input("You: ")
        if q.lower() == "exit":
            break
        print(replyToUser({"message": q}))