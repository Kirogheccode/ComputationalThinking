import sqlite3

def load_foods_from_sqlite(db_path="foody_data.sqlite"):
    foods = []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            id, 
            "Name",
            "Location",
            "Rating",
            "Local Image Path"
        FROM Restaurants
    """)

    rows = cursor.fetchall()

    for row in rows:
        foods.append({
            "id": row[0],     
            "name": row[1],    
            "location": row[2],
            "rating": row[3],
            "image": row[4].replace("\\", "/") if row[4] else None
        })

    conn.close()
    return foods