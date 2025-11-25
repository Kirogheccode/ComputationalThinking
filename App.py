import os
import json
import sqlite3
import math
import requests
import chromadb
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
from sentence_transformers import SentenceTransformer

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

# Load the embedding model once when the bot starts
print("Loading embedding model...")
embedder = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded.")


# --- 2. HELPER FUNCTIONS ---

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers.
    return c * r


def get_coords_for_location(location_name):
    """
    Uses Geoapify to geocode a user's location query (e.g., "District 1")
    """
    # Bias search results to Ho Chi Minh City
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
    Creates a square bounding box around a point.
    1 degree of latitude is ~111km.
    """
    lat_change = distance_km / 111.0
    # Longitude change depends on the latitude (cosine factor)
    lon_change = distance_km / (111.0 * math.cos(math.radians(lat)))

    return {
        "min_lat": lat - lat_change,
        "max_lat": lat + lat_change,
        "min_lon": lon - lon_change,
        "max_lon": lon + lon_change
    }


# --- 3. MISSION HANDLERS ---

def handle_culture_query(prompt):
    print("-> Executing: Culture Query")
    system_context = (
        "You are a friendly and knowledgeable Vietnamese cultural expert. "
        "Answer the user's question clearly, concisely, and with a respectful tone."
    )
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content([system_context, prompt])
    return response.text


def route_user_request(prompt):
    system_context = (
        "You are a helpful travel assistant AI for Vietnam. "
        "Your job is to analyze the user's prompt and classify their intent into one of three tasks. "
        "You must also extract any relevant entities."
        "\n"
        "The 3 tasks are:\n"
        "1. 'culture_query': User is asking for general information.\n"
        "2. 'food_recommendation': User is asking for a *type* of food.\n"
        "3. 'restaurant_recommendation': User is asking for a specific *place* to eat.\n"
        "\n"
        "**Extraction Rules:**\n"
        "- If the task is 'restaurant_recommendation', the 'cuisine' is the specific food (e.g., 'Cơm tấm').\n"
        "- The 'location' is the geographical area (e.g., 'district 5').\n"
        "- If a field is not present, set its value to 'none'."
    )

    schema = {
        "type": "OBJECT",
        "properties": {
            "task": {"type": "STRING"},
            "location": {"type": "STRING"},
            "cuisine": {"type": "STRING"},
            "diet_ingredient": {"type": "STRING"}
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
    """
    Mission 3: Recommends a restaurant using SQLite spatial filtering + Python Text Search.
    """
    location = entities.get('location')
    cuisine = entities.get('cuisine')

    print(f"-> Executing: Restaurant Recommendation (Location: {location}, Cuisine: {cuisine})")

    # 1. Geocode the User's Location
    user_lat, user_lon = None, None
    if location and location.lower() != 'none':
        user_lat, user_lon = get_coords_for_location(location)

    # 2. Build the SQL Query (FILTER ONLY BY LOCATION to handle Vietnamese text in Python)
    conn = sqlite3.connect('foody_data.sqlite')  # Ensure this matches your actual DB file name
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM Restaurants"
    params = []
    conditions = []

    # Use a bounding box to get candidates (e.g., 10km radius)
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

    # 3. Process & Filter in Python
    results = []

    # Normalize search term for better matching
    search_term = cuisine.lower() if cuisine else ""

    for row in rows:
        rest = dict(row)
        rest_name = str(rest['Name']).lower()  # Ensure string conversion

        # FILTER BY CUISINE (Python Logic - Better for Vietnamese)
        if search_term and search_term not in rest_name:
            continue  # Skip if cuisine doesn't match

        # --- FIX 1: Convert Rating to Float ---
        try:
            rest['Rating'] = float(rest['Rating'])
        except (ValueError, TypeError):
            rest['Rating'] = 0.0

        # --- FIX 2: Calculate Distance ---
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

    if not results:
        return f"I couldn't find any restaurants matching '{cuisine}' near '{location}'."

    # 4. Rank the Results
    results.sort(key=lambda x: (-x['Rating'], x['distance_km']))
    top_results = results[:50]

    # 5. Send to Gemini
    restaurant_context = json.dumps(top_results, ensure_ascii=False)

    system_context = (
        "You are a local restaurant guide. Your job is to recommend 3-5 top restaurants to the user. "
        "Use the provided JSON database. "
        "The JSON includes a 'distance_km' field showing how far the restaurant is from the user. "
        "Mention this distance in your answer (e.g. 'It is just 1.5km away'). "
        f"USER LOCATION: {location}\n"
        f"USER CUISINE: {cuisine}\n"
        f"DATABASE:\n{restaurant_context}"
    )

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content([system_context, prompt])
    return response.text


def handle_food_recommendation(prompt, entities):
    """
    Mission 2: Recommends a dish using Local RAG (Vector Search).
    """
    diet = entities.get('diet_ingredient')
    print(f"-> Executing: Food Recommendation (Diet: {diet})")

    # Connect to ChromaDB
    try:
        db_client = chromadb.PersistentClient(path="chroma_db")
        collection = db_client.get_collection(name="recipes")
    except Exception as e:
        return f"Error connecting to recipe database. Please run 'preprocess_recipes_rag.py' first. ({e})"

    # Embed Search
    search_text = f"{prompt} {diet}"
    query_embedding = embedder.encode(search_text).tolist()

    # Query
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )

    if not results['documents']:
        return "I'm sorry, I couldn't find any recipes."

    found_recipes_text = results['documents'][0]

    system_context = (
            "You are a Vietnamese food expert. Recommend a dish based on the results below.\n"
            "SEARCH RESULTS (RAG Context):\n" +
            "\n---\n".join(found_recipes_text)
    )

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content([system_context, "User Request: " + prompt])
    return response.text


# --- 4. MAIN LOOP ---

def main_chatbot():
    print("\n--- 🤖 Welcome to the Vietnam Cultural & Food Consultant ---")
    print("I can help you with culture, food, or restaurant recommendations.")
    print("Type 'exit' or 'quit' to end the chat.\n")

    while True:
        prompt = input("You: ")
        if prompt.lower() in ['exit', 'quit']:
            print("Gemini: Cảm ơn! See you again!")
            break

        # 1. Route
        task_data = route_user_request(prompt)
        task_type = task_data.get('task')

        # 2. Handle
        try:
            if task_type == 'culture_query':
                response = handle_culture_query(prompt)
            elif task_type == 'food_recommendation':
                response = handle_food_recommendation(prompt, task_data)
            elif task_type == 'restaurant_recommendation':
                response = handle_restaurant_recommendation(prompt, task_data)
            else:
                response = "I'm sorry, I'm not sure how to help with that."

            print(f"\nGemini: {response}\n")

        except Exception as e:
            print(f"\nGemini: Error occurred: {e}\n")


if __name__ == "__main__":
    main_chatbot()