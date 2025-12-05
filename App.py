import os
import json
import sqlite3
import math
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

# --- 1. CONFIGURATION ---

load_dotenv()
GOOGLE_API = os.getenv("GOOGLE_API_KEY")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")

if GOOGLE_API:
    genai.configure(api_key=GOOGLE_API)
else:
    print("Error: GOOGLE_API_KEY not found.")
    exit()

if not GEOAPIFY_API_KEY:
    print("Error: GEOAPIFY_API_KEY not found.")
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
    api_key = os.getenv("SPOONACULAR_API_KEY")
    if not api_key: return None

    # We use 'complexSearch' to find the closest matching recipe and get its stats
    url = "https://api.spoonacular.com/recipes/complexSearch"
    params = {
        "apiKey": api_key,
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
                    if n['name'] == name: return f"{n['amount']}{n['unit']}"
                return "?"

            return f"({item['title']}: {find_n('Calories')} kcal, Protein {find_n('Protein')}, Fat {find_n('Fat')})"
    except Exception as e:
        print(f"Spoonacular Error for {dish_name}: {e}")

    return None

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
    """
    STRICT ROUTER:
    1. '/place_' or '/eat' -> Restaurant Recommendation
    2. '/recipe_' or '/cook' -> Food Recommendation
    3. '/plan_' or '/menu' -> Daily Menu
    4. EVERYTHING ELSE -> Culture Query (Default)
    """
    prompt_lower = prompt.strip().lower()

    # --- 1. Restaurant Command ---
    # Syntax: "/eat Cơm tấm quận 1" or "/place_ Cơm tấm quận 1"
    if prompt_lower.startswith("/place_") or prompt_lower.startswith("/eat"):
        # Remove the command to get the query
        clean_prompt = prompt.replace("/place_", "").replace("/eat", "").strip()

        # Simple split logic: Try to separate Dish vs Location by common separators
        # This is a basic heuristic since we aren't using the LLM for extraction anymore
        cuisine = clean_prompt
        location = "none"

        # Check for location keywords to split string manually
        loc_markers = [" tại ", " ở ", " quận ", " district ", " đường ", " street ", " near ", " gần "]
        for marker in loc_markers:
            if marker in clean_prompt.lower():
                parts = clean_prompt.lower().split(marker, 1)
                # Re-slice the original string to keep case
                idx = clean_prompt.lower().find(marker)
                cuisine = clean_prompt[:idx].strip()
                location = clean_prompt[idx:].strip()  # Keep the marker (e.g. "quan 1") as part of location
                break

        return {
            "task": "restaurant_recommendation",
            "cuisine": cuisine,
            "location": location,
            "category": "",
            "budget": ""
        }

    # --- 2. Recipe/Food Command ---
    # Syntax: "/cook Phở bò"
    if prompt_lower.startswith("/recipe_") or prompt_lower.startswith("/cook"):
        clean_prompt = prompt.replace("/recipe_", "").replace("/cook", "").strip()
        return {
            "task": "food_recommendation",
            "cuisine": clean_prompt,  # The whole text is the dish name
            "diet_ingredient": "General"  # Default
        }

    # --- 3. Menu Command ---
    # Syntax: "/plan" or "/menu"
    if prompt_lower.startswith("/plan_") or prompt_lower.startswith("/menu"):
        return {
            "task": "daily_menu",
            "location": "none",  # Default
            "budget": "moderate"
        }

    # --- 4. DEFAULT CATCH-ALL (Culture Query) ---
    # If no command is found, we assume it's a general conversation/culture question.
    print("-> Router: No command found. Defaulting to Culture Query.")
    return {"task": "culture_query"}

def handle_restaurant_recommendation(prompt, entities, user_profile=None):
    """
    Mission 3: Recommends restaurants.
    PRIORITY: Location > Cuisine.
    SOFT FILTERS: Time, Tags, Price (Warns instead of removing).
    """
    location = entities.get('location')
    cuisine = entities.get('cuisine')
    category = entities.get('category', '').lower()  # Tags like "student", "family"
    budget = entities.get('budget', '').lower()

    # Fallback for cuisine if command-based
    if not cuisine and (prompt.startswith("/eat") or prompt.startswith("/tim quan")):
        parts = prompt.split(" ", 1)
        cuisine = parts[1] if len(parts) > 1 else ""

    print(f"-> Restaurant Rec: Loc='{location}', Dish='{cuisine}', Tag='{category}', Budget='{budget}'")

    # 1. Geocode (Strict Location Filter)
    user_lat, user_lon = None, None
    if location and location.lower() != 'none':
        user_lat, user_lon = get_coords_for_location(location)

    # 2. SQL Query (Location + Broad Cuisine)
    conn = sqlite3.connect('foody_data.sqlite')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM restaurants"
    params = []

    # Strict Location Filter (SQL)
    if user_lat:
        bbox = get_bounding_box(user_lat, user_lon, 10)
        query += " WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?"
        params.extend([bbox['min_lat'], bbox['max_lat'], bbox['min_lon'], bbox['max_lon']])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # 3. Python Filter (Soft Filters)
    results = []
    search_term = cuisine.lower() if cuisine and cuisine != 'none' else ""

    for r in rows:
        val = dict(r)
        val['warnings'] = []  # Store warnings here

        # A. Cuisine Filter (Keep Strict - User needs the right food)
        if search_term and search_term not in val['name'].lower():
            continue

        # B. Opening Hours (Soft Filter)
        if not is_open_now(val['opening_hours']):
            val['warnings'].append("CLOSED NOW")

        # C. Tag/Category (Soft Filter)
        db_tags = str(val.get('tags', '')).lower()
        if category and category != 'none':
            if category not in db_tags:
                val['warnings'].append(f"Tag '{category}' not found")

        # D. Price Check (Soft Filter)
        price_info = str(val.get('price_range', '')).lower()
        if price_info == 'updating':
            val['warnings'].append("Price is Updating")

        # Data cleanup
        try:
            val['rating'] = float(val['rating'])
        except:
            val['rating'] = 0.0

        if user_lat:
            val['dist'] = round(haversine(user_lat, user_lon, val['latitude'], val['longitude']), 2)
        else:
            val['dist'] = 0

        results.append(val)

    # Fallback
    if not results:
        model = genai.GenerativeModel('gemini-2.5-flash')
        return model.generate_content(
            f"User asked for '{cuisine}' near '{location}'. No location matches found in DB. Suggest general cultural info.").text

    # 4. Rank
    # Primary Sort: Number of Warnings (Ascending) -> Perfect matches first
    # Secondary Sort: Rating (Descending)
    # Tertiary Sort: Distance (Ascending)
    results.sort(key=lambda x: (len(x['warnings']), -x['rating'], x['dist']))

    top_5 = results[:5]

    # 5. Final Response
    model = genai.GenerativeModel('gemini-2.5-flash')
    sys_msg = (
        "Recommend 3-5 restaurants from the list below.\n"
        f"Context: User is looking for '{cuisine}' in '{location}'.\n"
        "**CRITICAL INSTRUCTION:**\n"
        "The data contains a 'warnings' list for each restaurant.\n"
        "- If 'warnings' is empty, recommend it normally.\n"
        "- If 'warnings' has items (e.g. ['CLOSED NOW']), you MUST mention this clearly to the user "
        "(e.g. 'Highly rated, but currently closed' or 'Note: Price is updating').\n"
        "Provide estimated nutritional breakdown for the main dish.\n"
        f"List:\n{json.dumps(top_5, ensure_ascii=False, default=str)}"
    )
    return model.generate_content([sys_msg, prompt]).text


def handle_food_recommendation(prompt, entities):
    diet = entities.get('diet_ingredient', 'General')
    print(f"-> Food Rec (Direct LLM): {diet}")
    model = genai.GenerativeModel('gemini-2.5-flash')
    sys_msg = (
        f"You are an expert Vietnamese culinary. User wants a dish suggestion. Diet: {diet}.\n"
        "1. Recommend specific authentic Vietnamese dishes (english reply) or if users mention certain dishes, focus the answer on them.\n"
        "2. Warn if dish conflicts with restrictions (e.g. Pork/Halal).\n"
        "3. Provide estimated Calories/Protein/Carbs/Fat and cost."
    )
    return model.generate_content([sys_msg, prompt]).text


def handle_daily_menu(prompt, entities, user_profile=None):
    """
    Mission 4:
    1. Gemini decides the authentic Vietnamese Menu.
    2. Python asks Spoonacular for the Nutrition of those specific dishes.
    3. Gemini presents the final result.
    """
    budget = entities.get('budget', 'moderate')
    diet = entities.get('diet_ingredient', '')
    if user_profile and not diet:
        diet = user_profile.get('diet_restrictions', '')

    print(f"-> Daily Menu (Hybrid): Diet={diet}, Budget={budget}")

    # --- STAGE 1: ASK GEMINI FOR DISH NAMES (Structured JSON) ---
    model = genai.GenerativeModel('gemini-2.5-flash')

    # We force Gemini to output JSON so we can read it easily in Python
    json_prompt = (
        f"Create a 1-Day Vietnamese Meal Plan (Breakfast, Lunch, Dinner) (english reply). Diet: {diet}.\n"
        "Return ONLY a valid JSON object with keys 'breakfast', 'lunch', 'dinner'.\n"
        "Value should be the Vietnamese dish name, avoid the options that users have to cook themselves (e.g. 'Pho Bo').\n"
        "Do not add markdown formatting."
    )

    try:
        # Get dish names
        json_response = model.generate_content(json_prompt).text
        # Clean potential markdown codes if Gemini adds them
        clean_json = json_response.replace("```json", "").replace("```", "").strip()
        menu_plan = json.loads(clean_json)
    except Exception as e:
        # Fallback if JSON fails
        return handle_daily_menu_fallback(prompt)

    # --- STAGE 2: FETCH NUTRITION FOR THESE DISHES ---
    nutrition_info = {}
    total_cals = 0

    print("   Fetching Spoonacular Data...")
    for meal, dish in menu_plan.items():
        stats = get_nutrition_from_spoonacular(dish)
        if stats:
            nutrition_info[meal] = stats
        else:
            nutrition_info[meal] = "(Nutrition data unavailable)"

    # --- STAGE 3: GENERATE FINAL PRESENTATION ---
    final_context = (
        "You are a Vietnamese Culinary Expert.\n"
        "Here is the Menu you planned, combined with Lab Data (english reply):\n"
        f"- Breakfast: {menu_plan['breakfast']} {nutrition_info['breakfast']}\n"
        f"- Lunch: {menu_plan['lunch']} {nutrition_info['lunch']}\n"
        f"- Dinner: {menu_plan['dinner']} {nutrition_info['dinner']}\n\n"
        "**TASK:**\n"
        "1. Present this menu beautifully.\n"
        "2. Describe the cultural significance of each dish briefly.\n"
        "3. Comment on the nutritional balance based on the data provided."
    )

    return model.generate_content([final_context, f"User Request: {prompt}"]).text


def handle_daily_menu_fallback(prompt):
    # Simple backup if JSON parsing fails
    model = genai.GenerativeModel('gemini-2.5-flash')
    return model.generate_content(f"Create a Vietnamese meal plan for: {prompt}").text

    return model.generate_content([sys_msg, prompt]).text

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


if __name__ == "__main__":
    main_chatbot()