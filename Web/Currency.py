import requests
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. CONFIGURATION ---
load_dotenv()

# Currency API (ExchangeRate-API v6)
CURRENCY_API_KEY = os.getenv("CURRENCY_API_KEY")
BASE_URL = "https://v6.exchangerate-api.com/v6"

# Gemini API (for Image Scanning)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# Supported Currencies for Dropdown
SUPPORTED_CURRENCIES = {
    "1": "USD",
    "2": "EUR",
    "3": "JPY",
    "4": "GBP",
    "5": "AUD",
    "6": "CNY"
}

# Mapping codes to names for better display
CURRENCY_NAMES = {
    "USD": "United States Dollar",
    "EUR": "Euro",
    "JPY": "Japanese Yen",
    "GBP": "British Pound",
    "AUD": "Australian Dollar",
    "CNY": "Chinese Yuan",
    "VND": "Vietnamese Dong"
}


# --- 2. HELPER FUNCTIONS ---

def get_exchange_rate(foreign_currency):
    """
    Fetches the rate for Foreign -> VND using ExchangeRate-API.
    """
    if not CURRENCY_API_KEY:
        return {"success": False, "error": "API Key not found in .env"}

    # Construct URL: /v6/YOUR-API-KEY/pair/FROM/TO
    url = f"{BASE_URL}/{CURRENCY_API_KEY}/pair/{foreign_currency}/VND"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if data.get("result") == "success":
            return {
                "success": True,
                "rate": float(data["conversion_rate"]),
                "name": CURRENCY_NAMES.get(foreign_currency, foreign_currency)
            }
        else:
            return {
                "success": False,
                "error": data.get("error-type", "Unknown API error")
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


def scan_money_image(image_path):
    """
    Uses Gemini 2.5 Flash to analyze an image of money.
    Strict Mode: Rejects image if more than 1 money item is found.
    """
    try:
        if not GOOGLE_API_KEY:
            return {"success": False, "error": "Google API Key missing"}

        # Upload the file to Gemini
        sample_file = genai.upload_file(path=image_path, display_name="User Money Upload")

        # Initialize Model
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")

        # Prompt asking for item count and value
        prompt = (
            "Analyze this image of money.\n"
            "1. Identify the Currency Code (e.g., USD, VND, EUR).\n"
            "2. Count the EXACT number of distinct bills or coins visible.\n"
            "3. Calculate the total monetary value.\n"
            "4. Check for signs of fake money.\n"
            "Return ONLY a raw JSON string (no markdown) with this format:\n"
            "{ \"amount\": number, \"currency\": \"CODE\", \"item_count\": number, \"warning\": \"message_or_null\" }"
        )

        response = model.generate_content([sample_file, prompt])

        # Parse result
        text_resp = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text_resp)

        # Check Item Count
        item_count = data.get("item_count", 1)
        if item_count > 1:
            return {
                "success": False,
                "error": f"Detected {item_count} items. Please upload an image of a SINGLE bill or coin."
            }

        return {"success": True, "data": data}

    except Exception as e:
        print(f"Gemini Vision Error: {e}")
        return {"success": False, "error": "Could not recognize money in this image."}


def calculate_conversion(amount, currency_code, direction):
    """
    Performs the math for the conversion.
    direction '1': Foreign -> VND
    direction '2': VND -> Foreign
    """
    # 1. Get the Rate (Always Foreign -> VND)
    rate_data = get_exchange_rate(currency_code)

    if not rate_data["success"]:
        return rate_data  # Return the error from API

    rate = rate_data["rate"]
    result_amount = 0
    formatted_result = ""
    exchange_rate_display = ""

    # 2. Do the Math
    if direction == '1':  # Foreign -> VND (Multiplication)
        result_amount = amount * rate
        formatted_result = f"{result_amount:,.0f} VND"
        exchange_rate_display = f"1 {currency_code} = {rate:,.0f} VND"

    else:  # VND -> Foreign (Division)
        result_amount = amount / rate
        formatted_result = f"{result_amount:,.2f} {currency_code}"
        inverse_rate = 1 / rate
        exchange_rate_display = f"1 VND ≈ {inverse_rate:.6f} {currency_code}"

    return {
        "success": True,
        "original_amount": amount,
        "converted_string": formatted_result,
        "rate_display": exchange_rate_display
    }