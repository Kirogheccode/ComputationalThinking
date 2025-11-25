import pandas as pd
import sqlite3
import os

# --- Configuration ---
INPUT_CSV = "foody_data_lat_long.csv"
OUTPUT_DB = "foody_data.sqlite"  # This will replace your old small DB


def main():
    print(f"--- Converting {INPUT_CSV} to SQLite ---")

    # 1. Load the CSV
    try:
        df = pd.read_csv(INPUT_CSV)
        print(f"Loaded {len(df)} restaurants.")
    except FileNotFoundError:
        print(f"Error: Could not find '{INPUT_CSV}'.")
        return

    # 2. Validation (Check for the columns we need)
    required_cols = ['Name', 'Location', 'Rating', 'Latitude', 'Longitude']
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        print(f"Error: The CSV is missing these columns: {missing_cols}")
        return

    # 3. Clean Data (Ensure coordinates are numbers)
    # Drop rows where Latitude or Longitude is missing/empty
    original_count = len(df)
    df = df.dropna(subset=['Latitude', 'Longitude'])

    # Ensure they are floats (numbers), not strings
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')

    # Drop again in case 'to_numeric' created any NaNs from bad strings
    df = df.dropna(subset=['Latitude', 'Longitude'])

    if len(df) < original_count:
        print(f"Removed {original_count - len(df)} rows with invalid coordinates.")

    # 4. Save to SQLite
    print(f"Saving {len(df)} rows to database...")
    conn = sqlite3.connect(OUTPUT_DB)

    # 'if_exists="replace"' will overwrite your old small table with this new big one
    df.to_sql('Restaurants', conn, if_exists='replace', index=False)

    conn.close()
    print(f"✅ Success! Database '{OUTPUT_DB}' has been updated.")


if __name__ == "__main__":
    main()