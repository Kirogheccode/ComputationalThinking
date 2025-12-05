import sqlite3

def load_foods_from_sqlite(db_path="data/foody_data.sqlite"):
    foods = []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            id, 
            name,
            location,
            rating,
            price_range,
            opening_hours,
            local_image_path
        FROM restaurants
    """)

    rows = cursor.fetchall()

    for row in rows:
        foods.append({
            "id": row[0],     
            "name": row[1],    
            "location": row[2],
            "rating": row[3],
            "price": row[4] if row[4] else "Đang cập nhật",      
            "hours": row[5] if row[5] else "Đang cập nhật",      
            "image": row[6].replace("\\", "/") if row[6] else None
        })

    conn.close()
    return foods