import requests
import os
from dotenv import load_dotenv

load_dotenv()
# Ensure this key is in your .env file
API_KEY = os.getenv("CURRENCY_API_KEY")
API_ENDPOINT = "https://api.getgeoapi.com/v2/currency/convert"

SUPPORTED_CURRENCIES = {
    "1": "USD",
    "2": "EUR",
    "3": "JPY",
    "4": "GBP",
    "5": "AUD",
    "6": "CNY"
}


def get_exchange_rate(foreign_currency):
    """
    Fetches the rate for Foreign -> VND.
    """
    if not API_KEY:
        return {"success": False, "error": "API Key not found"}

    params = {
        "api_key": API_KEY,
        "from": foreign_currency,
        "to": "VND",
        "amount": 1,
        "format": "json"
    }

    try:
        response = requests.get(API_ENDPOINT, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            return {
                "success": True,
                "rate": float(data["rates"]["VND"]["rate"]),
                "name": data["rates"]["VND"]["currency_name"]
            }
        else:
            return {"success": False, "error": data.get("error", {}).get("message", "Unknown API error")}

    except Exception as e:
        return {"success": False, "error": str(e)}


def calculate_conversion(amount, currency_code, direction):
    """
    Logic extracted from your main() loop
    direction '1': Foreign -> VND
    direction '2': VND -> Foreign
    """
    rate_data = get_exchange_rate(currency_code)

    if not rate_data["success"]:
        return rate_data  # Return the error

    rate = rate_data["rate"]
    result_amount = 0
    formatted_result = ""
    exchange_rate_display = ""

    if direction == '1':  # Foreign -> VND
        result_amount = amount * rate
        formatted_result = f"{result_amount:,.0f} VND"
        exchange_rate_display = f"1 {currency_code} = {rate:,.0f} VND"
    else:  # VND -> Foreign
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