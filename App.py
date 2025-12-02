import os
import json
import sqlite3
import math
import requests
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai

# --- 1. CONFIGURATION AND GLOBAL DATA LOADING ---

# Load .env file (for GOOGLE_API_KEY)
load_dotenv()
GOOGLE_API = os.getenv("GOOGLE_API_KEY")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")

if GOOGLE_API:
    genai.configure(api_key=GOOGLE_API)
else:
    print("Error: GOOGLE_API_KEY not found. Please check your .env file.")
    exit()

if not GEOAPIFY_API_KEY:
    print("Error: GEOAPIFY_API_KEY not found. Please check your .env file.")
    exit()

# --- DIET KNOWLEDGE BASE ---
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

# --- USER DATABASE MANAGER ---
USER_DB = "user_data.sqlite"


def init_user_db():
    """Creates the Users table if it doesn't exist."""
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            username TEXT PRIMARY KEY,
            diet_restrictions TEXT,
            food_priorities TEXT
        )
    ''')
    conn.commit()
    conn.close()


def get_user_profile(username):
    conn = sqlite3.connect(USER_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def save_user_profile(username, diet, priorities):
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO Users (username, diet_restrictions, food_priorities)
        VALUES (?, ?, ?)
    ''', (username, diet, priorities))
    conn.commit()
    conn.close()


# --- 2. HELPER FUNCTIONS ---

def haversine(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371
    return c * r


def get_coords_for_location(location_name):
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
        if response.ok:
            data = response.json()
            if data['features']:
                coords = data['features'][0]['geometry']['coordinates']
                return coords[1], coords[0]  # Lat, Lon
    except Exception as e:
        print(f"Error geocoding: {e}")
    return None, None


def get_bounding_box(lat, lon, distance_km):
    lat_change = distance_km / 111.0
    lon_change = distance_km / (111.0 * math.cos(math.radians(lat)))
    return {
        "min_lat": lat - lat_change, "max_lat": lat + lat_change,
        "min_lon": lon - lon_change, "max_lon": lon + lon_change
    }


# --- 3. MISSION HANDLERS ---

def handle_culture_query(prompt):
    print("-> Executing: Culture Query")
    model = genai.GenerativeModel('gemini-2.5-flash')
    sys_msg = "You are a Vietnamese cultural expert. Answer clearly. If the topic involves food taboos (e.g. Pork in Islam), explicitly mention them."
    return model.generate_content([sys_msg, prompt]).text


def route_user_request(prompt):
    # Updated to extract 'budget'
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
            "budget": {"type": "STRING"}  # <--- New Field
        },
        "required": ["task"]
    }
    model = genai.GenerativeModel('gemini-2.5-flash')
    try:
        res = model.generate_content([system_context, prompt],
                                     generation_config={"response_mime_type": "application/json",
                                                        "response_schema": schema})
        return json.loads(res.text)
    except:
        return {"task": "unknown"}


def handle_restaurant_recommendation(prompt, entities, user_profile=None):
    location = entities.get('location')
    cuisine = entities.get('cuisine')
    budget = entities.get('budget', 'any')  # <--- Get Budget

    print(f"-> Restaurant Rec: {location}, {cuisine}, Budget: {budget}")

    # 1. Geocode
    user_lat, user_lon = None, None
    if location and location.lower() != 'none':
        user_lat, user_lon = get_coords_for_location(location)

    # 2. SQL Query
    conn = sqlite3.connect('foody_data.sqlite')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = "SELECT * FROM Restaurants"
    params = []

    if user_lat:
        bbox = get_bounding_box(user_lat, user_lon, 10)
        query += " WHERE Latitude BETWEEN ? AND ? AND Longitude BETWEEN ? AND ?"
        params.extend([bbox['min_lat'], bbox['max_lat'], bbox['min_lon'], bbox['max_lon']])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # 3. Process
    results = []
    search_term = cuisine.lower() if cuisine and cuisine != 'none' else ""

    # Memory Context
    memory_context = ""
    if user_profile:
        memory_context = f"\n**USER PROFILE:** Diet: {user_profile['diet_restrictions']}, Prefs: {user_profile['food_priorities']}"

    for row in rows:
        rest = dict(row)
        if search_term and search_term not in rest['Name'].lower(): continue

        try:
            rest['Rating'] = float(rest['Rating'])
        except:
            rest['Rating'] = 0.0

        if user_lat:
            rest['distance_km'] = round(haversine(user_lat, user_lon, rest['Latitude'], rest['Longitude']), 2)
        else:
            rest['distance_km'] = 0
        results.append(rest)

    # Fallback
    model = genai.GenerativeModel('gemini-2.5-flash')
    if not results:
        fallback_msg = (
            f"User asked for '{cuisine}' near '{location}' (Budget: {budget}). No DB matches.\n"
            "1. Politely apologize for missing data.\n"
            "2. Provide general cultural info about the dish.\n"
            "3. **Estimate the typical price** for this dish in Vietnam (e.g. 'Usually 30k-50k')."
        )
        return model.generate_content(fallback_msg).text

    # Rank
    results.sort(key=lambda x: (-x['Rating'], x['distance_km']))
    top_5 = results[:5]

    # 4. Final Response with Cost Estimation
    sys_msg = (
        "Recommend restaurants from the list below.\n"
        f"User Budget Preference: {budget}.\n"
        f"{memory_context}\n"
        "**CRITICAL INSTRUCTION:**\n"
        "For EACH restaurant, based on its name/type (e.g. 'Cơm Tấm' vs 'Nhà Hàng'), provide an **Estimated Cost** range in VND.\n"
        "- Street Food/Bình Dân: ~30k - 60k VND\n"
        "- Mid-range: ~80k - 150k VND\n"
        "- High-end: >200k VND\n"
        "Check if the estimated cost matches the User's Budget. If not, mention it (e.g. 'This is a bit pricier than your request').\n\n"
        f"DATA:\n{json.dumps(top_5, ensure_ascii=False)}"
    )
    return model.generate_content([sys_msg, prompt]).text


def handle_food_recommendation(prompt, entities, user_profile=None):
    diet = entities.get('diet_ingredient', 'General').lower()
    budget = entities.get('budget', 'any')
    print(f"-> Food Rec: {diet}, Budget: {budget}")

    # 1. Rules & Memory
    memory_context = ""
    active_rule = None
    for key in DIET_RULES:
        if key in diet:
            active_rule = DIET_RULES[key]
            break

    if active_rule:
        memory_context += f"\n**DIET RULE ({key.upper()}):** ❌ NO {', '.join(active_rule['prohibited'])}."
    if user_profile:
        memory_context += f"\n**USER PROFILE:** Restrictions: {user_profile['diet_restrictions']}"

    # 2. Direct LLM Response (No RAG needed for general food advice)
    model = genai.GenerativeModel('gemini-2.5-flash')

    sys_msg = (
        f"User wants a food suggestion. Request: {prompt}\n"
        f"Diet: {diet}. Budget: {budget}.\n"
        f"{memory_context}\n"
        "--------------------------------------------------\n"
        "1. Recommend 3 authentic Vietnamese dishes.\n"
        "2. **Safety Check:** Explain WHY it fits the diet (e.g. 'Safe for Halal because...').\n"
        "3. **Cost Estimation:** Provide a typical price range for this dish (Street vs Restaurant price).\n"
        "4. **Nutrient Detail:** Est. Calories/Protein/Carbs/Fat."
    )
    return model.generate_content([sys_msg, prompt]).text


def handle_daily_menu(prompt, entities, user_profile=None):
    budget = entities.get('budget', 'moderate')
    print(f"-> Daily Menu: Budget {budget}")

    # Simplified logic: Let Gemini act as the Chef using general knowledge
    model = genai.GenerativeModel('gemini-2.5-flash')

    profile_txt = f"User Profile: {user_profile['diet_restrictions']}" if user_profile else ""

    sys_msg = (
        f"Create a 1-Day Vietnamese Meal Plan (Breakfast, Lunch, Dinner).\n"
        f"Budget Level: {budget}.\n"
        f"{profile_txt}\n"
        "1. Suggest specific dishes.\n"
        "2. **Total Cost:** Estimate the total daily cost in VND based on the budget level.\n"
        "3. **Nutrients:** Calculate approx total calories/protein for the day."
    )
    return model.generate_content([sys_msg, prompt]).text


# --- 4. MAIN ---

def main_chatbot():
    print("\n--- 🤖 Vietnam Food AI (Personalized & Cost-Aware) ---")
    init_user_db()

    # Login (Simplified for brevity)
    current_user = None
    choice = input("Do you have an account? (yes/no): ").lower()
    if choice in ['y', 'yes']:
        username = input("Enter username: ")
        current_user = get_user_profile(username)
        if current_user: print(f"Welcome {username}!")
    elif choice in ['n', 'no']:
        u = input("Username: ")
        d = input("Diet (Halal, Vegan...): ")
        p = input("Food Priorities: ")
        save_user_profile(u, d, p)
        current_user = get_user_profile(u)

    print("\nHow can I help? (Type 'exit' to quit)")
    while True:
        prompt = input("You: ")
        if prompt.lower() in ['exit', 'quit']: break

        try:
            data = route_user_request(prompt)
            task = data.get('task')

            if task == 'culture_query':
                resp = handle_culture_query(prompt)
            elif task == 'food_recommendation':
                resp = handle_food_recommendation(prompt, data, current_user)
            elif task == 'restaurant_recommendation':
                resp = handle_restaurant_recommendation(prompt, data, current_user)
            elif task == 'daily_menu':
                resp = handle_daily_menu(prompt, data, current_user)
            else:
                resp = "I'm not sure how to help."

            print(f"\nGemini: {resp}\n")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main_chatbot()