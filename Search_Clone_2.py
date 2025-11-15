import os
import json
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai

# --- 1. CONFIGURATION AND GLOBAL DATA LOADING ---

# Load .env file (for GOOGLE_API_KEY)
load_dotenv()
GOOGLE_API = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API:
    genai.configure(api_key=GOOGLE_API)
else:
    print("Error: GOOGLE_API_KEY not found. Please check your .env file.")
    exit()

# Load all CSV data into memory (as pandas DataFrames)
try:
    print("Loading CSV data...")
    savourthepho_recipes_df = pd.read_csv("savourthepho_recipes.csv")
    foody_data_df = pd.read_csv("foody_data_manual.csv")
    print("Data loaded successfully.")
except FileNotFoundError as e:
    print(f"Error: Could not find a required CSV file. {e}")
    print("Please make sure 'savourthepho_recipes.csv' and 'foody_data_manual.csv' are in the same directory.")
    exit()


# --- 2. THE "ROUTER" - DECIDES THE USER'S INTENT ---

def handle_culture_query(prompt):
    """
    Mission 1: Answers general cultural questions.
    """
    print("-> Executing: Culture Query")
    system_context = (
        "You are a friendly and knowledgeable Vietnamese cultural expert. "
        "Answer the user's question clearly, concisely, and with a respectful tone."
    )

    # --- FIX ---
    model = genai.GenerativeModel('gemini-2.5-flash')  # Changed from gemini-pro
    # --- END FIX ---

    response = model.generate_content([system_context, prompt])
    return response.text

def route_user_request(prompt):
    """
    Uses Gemini to classify the user's intent and extract key entities.
    This is the "brain" of the chatbot.
    """
    system_context = (
        "You are a helpful travel assistant AI for Vietnam. "
        "Your job is to analyze the user's prompt and classify their intent into one of three tasks. "
        "You must also extract any relevant entities."
        "\n"
        "The 3 tasks are:\n"
        "1. 'culture_query': User is asking for general information (culture, holidays, festivals, habits, history, how-tos, explainers). (e.g., 'what is Tet?')\n"
        "2. 'food_recommendation': User is asking for a *type* of food (e.g., 'something vegetarian', 'a popular noodle soup', 'what should I eat for breakfast').\n"
        "3. 'restaurant_recommendation': User is asking for a specific *place* to eat (e.g., 'where can I find Banh Mi in District 1', 'best pho restaurant', 'Cơm tấm in district 5').\n"
        "\n"
        "**Extraction Rules:**\n"
        "- If the task is 'restaurant_recommendation', the 'cuisine' is the specific food they are looking for (e.g., 'Cơm tấm', 'Pho', 'Banh Mi').\n"
        "- The 'location' is the geographical area (e.g., 'district 5', 'Hanoi').\n"
        "- If a field is not present, set its value to 'none'."
    )

    schema = {
        "type": "OBJECT",
        "properties": {
            "task": {"type": "STRING",
                     "description": "One of: 'culture_query', 'food_recommendation', 'restaurant_recommendation', or 'unknown'."},
            "location": {"type": "STRING",
                         "description": "Any location mentioned, e.g., 'District 5', 'Hanoi'. Default 'none'."},
            "cuisine": {"type": "STRING",
                        "description": "Any specific food or dish, e.g., 'Cơm tấm', 'Pho'. Default 'none'."},
            "diet_ingredient": {"type": "STRING",
                                "description": "Any dietary restrictions, e.g., 'vegetarian', 'no peanuts'. Default 'none'."}
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
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error parsing router response: {e}")
        return {"task": "unknown"}
# --- 3. MISSION-SPECIFIC HANDLERS ---

def handle_restaurant_recommendation(prompt, entities):
    """
    Mission 3: Recommends a restaurant, using foody_data_manual.csv for context.
    """
    print(
        f"-> Executing: Restaurant Recommendation (Location: {entities.get('location')}, Cuisine: {entities.get('cuisine')})")

    # --- FIX: Changed column names to match your CSV ---
    ADDRESS_COL = 'Location'
    NAME_COL = 'Name'
    RATING_COL = 'Rating'
    # --- END FIX ---

    filtered_df = foody_data_df.copy()

    location = entities.get('location')
    cuisine = entities.get('cuisine')

    try:
        if location and location.lower() != 'none':
            # Search for location in the 'Location' column
            filtered_df = filtered_df[filtered_df[ADDRESS_COL].str.contains(location, case=False, na=False)]

        if cuisine and cuisine.lower() != 'none':
            # Search for cuisine in the 'Name' column
            filtered_df = filtered_df[filtered_df[NAME_COL].str.contains(cuisine, case=False, na=False)]

        if filtered_df.empty:
            return f"I'm sorry, I couldn't find any restaurants matching '{cuisine}' in '{location}' in my database."

        # Sort by rating and take the top 50 as context
        filtered_df = filtered_df.sort_values(by=RATING_COL, ascending=False).head(50)

        # Select only the columns Gemini needs, to save tokens
        context_df = filtered_df[[NAME_COL, ADDRESS_COL, RATING_COL]]
        restaurant_context = context_df.to_json(orient='records', force_ascii=False)

    except KeyError as e:
        print(f"--- FATAL ERROR ---")
        print(f"A column is missing from your 'foody_data_manual.csv' file.")
        print(f"The code tried to find: {e}")
        print(
            f"Please check the headers in your CSV and update the variables (ADDRESS_COL, NAME_COL, RATING_COL) in this function.")
        return f"I'm sorry, I have a configuration error. My 'foody_data_manual.csv' file seems to be missing the {e} column."

    # --- FIX: Updated system prompt with correct column names ---
    system_context = (
        "You are a local restaurant guide. Your job is to recommend 3-5 top restaurants to the user. "
        "You must ONLY use the restaurants from the JSON list provided below. "
        f"Rank your recommendations by '{RATING_COL}' (highest first). "
        f"For each restaurant, list its '{NAME_COL}', '{ADDRESS_COL}', and '{RATING_COL}'.\n"
        f"USER'S LOCATION: {location}\n"
        f"USER'S CUISINE: {cuisine}\n\n"
        f"RESTAURANT DATABASE:\n{restaurant_context}"
    )
    # --- END FIX ---

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content([system_context, "User's request: " + prompt])
    return response.text
def handle_food_recommendation(prompt, entities):
    """
    Mission 2: Recommends a dish, using savourthepho_recipes.csv for context.
    """
    print(f"-> Executing: Food Recommendation (Diet: {entities.get('diet_ingredient')})")

    # Get a relevant sample from the recipe data
    # We sample to keep the prompt size efficient
    if len(savourthepho_recipes_df) > 100:
        recipe_sample_df = savourthepho_recipes_df.sample(100)
    else:
        recipe_sample_df = savourthepho_recipes_df

    recipe_context = recipe_sample_df.to_json(orient='records', force_ascii=False)

    system_context = (
        "You are a Vietnamese food blogger. Your job is to recommend a specific dish to the user. "
        "You should consider their request, especially any dietary needs or ingredient preferences.\n"
        f"USER'S DIET/PREFERENCE: {entities.get('diet_ingredient')}\n\n"
        "Use the following JSON list of recipes as your knowledge base. "
        "Recommend one or two dishes, explain what they are, and why they fit the user's request.\n"
        f"RECIPE KNOWLEDGE BASE:\n{recipe_context}"
    )

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content([system_context, "User's request: " + prompt])
    return response.text


def handle_food_recommendation(prompt, entities):
    """
    Mission 2: Recommends a dish, using savourthepho_recipes.csv for context.
    """
    print(f"-> Executing: Food Recommendation (Diet: {entities.get('diet_ingredient')})")

    # --- FIX: Select only the relevant columns ---
    recipe_df_filtered = savourthepho_recipes_df[['name', 'description', 'ingredients']]
    # --- END FIX ---

    # Get a relevant sample from the recipe data
    if len(recipe_df_filtered) > 100:
        recipe_sample_df = recipe_df_filtered.sample(100)
    else:
        recipe_sample_df = recipe_df_filtered

    recipe_context = recipe_sample_df.to_json(orient='records', force_ascii=False)

    system_context = (
        "You are a Vietnamese food blogger. Your job is to recommend a specific dish to the user. "
        "You should consider their request, especially any dietary needs or ingredient preferences.\n"
        f"USER'S DIET/PREFERENCE: {entities.get('diet_ingredient')}\n\n"
        "Use the following JSON list of recipes as your knowledge base. "
        "Recommend one or two dishes, explain what they are (using 'description'), what they contain (using 'ingredients'), "
        "and why they fit the user's request.\n"
        f"RECIPE KNOWLEDGE BASE:\n{recipe_context}"
    )

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content([system_context, "User's request: " + prompt])
    return response.text
# --- 4. MAIN CHATBOT LOOP ---

def main_chatbot():
    print("\n--- 🤖 Welcome to the Vietnam Cultural & Food Consultant ---")
    print("I can help you with culture, food, or restaurant recommendations.")
    print("Type 'exit' or 'quit' to end the chat.\n")

    while True:
        prompt = input("You: ")
        if prompt.lower() in ['exit', 'quit']:
            print("Gemini: Cảm ơn! (Thank you!) See you again!")
            break

        # --- Step 1: Route the request ---
        task_data = route_user_request(prompt)
        task_type = task_data.get('task')

        # --- Step 2: Execute the correct handler ---
        try:
            if task_type == 'culture_query':
                response = handle_culture_query(prompt)

            elif task_type == 'food_recommendation':
                response = handle_food_recommendation(prompt, task_data)

            elif task_type == 'restaurant_recommendation':
                response = handle_restaurant_recommendation(prompt, task_data)

            else:  # 'unknown' or other
                response = "I'm sorry, I'm not sure how to help with that. Could you rephrase your request?"

            print(f"\nGemini: {response}\n")

        except Exception as e:
            print(f"\nGemini: I'm sorry, an error occurred: {e}\n")


if __name__ == "__main__":
    main_chatbot()