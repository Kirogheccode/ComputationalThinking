import os
import time
import pandas as pd
import requests
from dotenv import load_dotenv

# Load .env file for API key
load_dotenv()
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")

if not GEOAPIFY_API_KEY:
    print("Error: GEOAPIFY_API_KEY not found in .env file.")
    print("Please get a key from geoapify.com and add it.")
    exit()

# Input and output file names
INPUT_CSV = "foody_data_manual.csv"
OUTPUT_CSV = "foody_data_geocoded.csv"


def geocode_address(address):
    """
Calls the Geoapify API to get lat/lon for a given address.
"""
    # We add "Ho Chi Minh City, Vietnam" to help the geocoder
    full_address = f"{address}, Ho Chi Minh City, Vietnam"

    try:
        url = "https://api.geoapify.com/v1/geocode/search"
        params = {
            'text': full_address,
            'apiKey': GEOAPIFY_API_KEY,
            'limit': 1
        }
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)

        data = response.json()

        if data['features']:
            # Get the coordinates from the first result
            geometry = data['features'][0]['geometry']
            if geometry['type'] == 'Point':
                lon, lat = geometry['coordinates']
                return lat, lon
        return None, None

    except requests.exceptions.RequestException as e:
        print(f"  > HTTP Error: {e}")
        return None, None
    except Exception as e:
        print(f"  > Error: {e}")
        return None, None


def main():
    print(f"Starting geocoding process for '{INPUT_CSV}'...")
    print("This may take several minutes. Please wait.")

    try:
        df = pd.read_csv(INPUT_CSV)
    except FileNotFoundError:
        print(f"Error: Could not find '{INPUT_CSV}'. Make sure it's in the same directory.")
        return

    # Create new columns for coordinates
    df['latitude'] = None
    df['longitude'] = None

    total = len(df)
    processed_count = 0
    success_count = 0

    # Loop through each row in the DataFrame
    for index, row in df.iterrows():
        # Using .at for faster cell access
        address = row.get('Location')

        if pd.isna(address):
            print(f"[{index + 1}/{total}] Skipping row with empty address.")
            continue

        print(f"[{index + 1}/{total}] Geocoding: {address[:50]}...")

        # Check if we already processed this (in case script was re-run)
        if pd.notna(row.get('latitude')):
            print("  > Already geocoded. Skipping.")
            success_count += 1
            continue

        lat, lon = geocode_address(address)

        if lat and lon:
            df.at[index, 'latitude'] = lat
            df.at[index, 'longitude'] = lon
            success_count += 1
            print(f"  > Success: ({lat}, {lon})")
        else:
            print("  > Failed to geocode.")

        processed_count += 1

        # IMPORTANT: Respect API rate limits
        # A short sleep prevents us from getting blocked by the server
        if processed_count % 5 == 0:  # Sleep every 5 requests
            time.sleep(1)

            # Save the new DataFrame to a new CSV
    try:
        df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
        print("\n--- Process Complete! ---")
        print(f"Successfully geocoded {success_count} out of {total} entries.")
        print(f"New file saved as: {OUTPUT_CSV}")
    except Exception as e:
        print(f"Error saving file: {e}")


if __name__ == "__main__":
    main()