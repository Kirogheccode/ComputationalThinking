import csv

def load_foods_from_csv(path="SideData\\foody_data.csv"):
    foods = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            foods.append({
                "name": row["Name"],
                "location": row["Location"],
                "rating": row["Rating"],
                "image": row["Local Image Path"].replace("\\", "/")
            })
    return foods