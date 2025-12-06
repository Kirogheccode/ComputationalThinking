import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("CURRENT_API_KEY")
API_ENDPOINT = "https://api.getgeoapi.com/v2/currency/convert"

# 2. CURRENCIES
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
    We always fetch this specific direction because the Free Plan
    often restricts the 'to' parameter to the account's base currency.
    """
    params = {
        "api_key": API_KEY,
        "from": foreign_currency,
        "to": "VND",
        "amount": 1,  # We just need the unit rate
        "format": "json"
    }

    try:
        print(f"   [i] Fetching live rate for 1 {foreign_currency} -> VND...")
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


def format_currency(amount, currency):
    """Formats numbers nicely (e.g., 25,000.00)"""
    # VND usually doesn't use decimals for small amounts, others do
    if currency == "VND":
        return f"{amount:,.0f} {currency}"
    return f"{amount:,.2f} {currency}"


def main():
    print("==========================================")
    print("      2-WAY CURRENCY CONVERTER 🇻🇳     ")
    print("==========================================")

    while True:
        # STEP 1: Choose the Foreign Currency
        print("\n--- Select Foreign Currency ---")
        for key, code in SUPPORTED_CURRENCIES.items():
            print(f" {key}. {code}")
        print(" q. Quit")

        choice = input("Option: ").strip().lower()
        if choice == 'q':
            print("Goodbye!")
            break

        if choice not in SUPPORTED_CURRENCIES:
            print("[!] Invalid selection.")
            continue

        foreign_code = SUPPORTED_CURRENCIES[choice]

        # STEP 2: Choose Direction
        print(f"\n--- Select Direction ---")
        print(f" 1. {foreign_code} -> VND (Buy VND)")
        print(f" 2. VND -> {foreign_code} (Sell VND)")

        direction = input("Option: ").strip()
        if direction not in ['1', '2']:
            print("[!] Invalid direction.")
            continue

        # STEP 3: Enter Amount
        try:
            input_currency = foreign_code if direction == '1' else "VND"
            amount_input = input(f"\nEnter amount in {input_currency}: ")
            amount = float(amount_input)
            if amount < 0: raise ValueError
        except ValueError:
            print("[!] Invalid amount. Enter a positive number.")
            continue

        # STEP 4: Process
        # We always fetch Foreign -> VND rate
        rate_data = get_exchange_rate(foreign_code)

        if not rate_data["success"]:
            print(f"[!] API Error: {rate_data['error']}")
            continue

        rate = rate_data["rate"]

        print("-" * 40)

        if direction == '1':  # Foreign -> VND
            converted_value = amount * rate
            print(f"💰 {format_currency(amount, foreign_code)} = {format_currency(converted_value, 'VND')}")
            print(f"   (Rate: 1 {foreign_code} = {format_currency(rate, 'VND')})")

        else:  # VND -> Foreign
            # Math: Amount / Rate
            converted_value = amount / rate
            print(f"💰 {format_currency(amount, 'VND')} = {format_currency(converted_value, foreign_code)}")
            # Show inverse rate for clarity
            inverse_rate = 1 / rate
            print(f"   (Rate: 1 VND ≈ {inverse_rate:.6f} {foreign_code})")

        print("-" * 40)


if __name__ == "__main__":
    main()