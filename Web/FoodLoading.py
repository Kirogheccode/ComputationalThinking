import sqlite3

def load_foods_from_sqlite(db_path="SideData\\foody_data.sqlite"):
    foods = []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            "Name",
            "Location",
            "Rating",
            "Local Image Path"
        FROM Restaurants
    """)

    rows = cursor.fetchall()

    for row in rows:
        foods.append({
            "name": row[0],
            "location": row[1],
            "rating": row[2],
            "image": row[3].replace("\\", "/") if row[3] else None
        })

    conn.close()
    return foods
