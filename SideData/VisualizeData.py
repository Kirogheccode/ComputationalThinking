import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re


def extract_district(location_str):
    """
    Extracts the district from a typical HCM address string.
    Assumes format ends with: ..., [District], TP. HCM
    """
    if not isinstance(location_str, str):
        return "Unknown"

    # Simple strategy: Split by comma and look for 'Quận' or 'Huyện' or 'Thành phố'
    parts = [p.strip() for p in location_str.split(',')]

    # Iterate backwards to find the district part
    for part in reversed(parts):
        # Check for District (Quận), District (Huyện), or specific cities like Thu Duc
        if re.search(r'^(Quận|Huyện|Thành phố|Thị xã)\s+', part, re.IGNORECASE):
            # Exclude the main city "Thành phố Hồ Chí Minh" or "TP. HCM" if it appears as a district
            if "hồ chí minh" not in part.lower() and "hcm" not in part.lower():
                return part
            # Special case for TP. Thu Duc which might be listed as a district equivalent
            if "thủ đức" in part.lower():
                return part

    # Fallback for simple "Quận X" pattern if strict splitting fails
    match = re.search(r'(Quận\s+[\w\d]+|Huyện\s+[\w\d]+)', location_str)
    if match:
        return match.group(1)

    return "Other"


def is_vegetarian(ingredients_text):
    """
    Determines if a recipe is vegetarian based on keywords in the ingredients.
    Returns True if Vegetarian (no meat), False otherwise.
    """
    if not isinstance(ingredients_text, str):
        return True  # Assume veg if no ingredients listed (safe default or skip)

    # List of non-vegetarian keywords (meats, seafood)
    # Note: Eggs and dairy are usually considered "Vegetarian" (Lacto-Ovo),
    # so we only filter out slaughter products.
    meat_keywords = [
        'pork', 'chicken', 'beef', 'fish', 'shrimp', 'crab', 'prawn',
        'meat', 'sausage', 'bacon', 'ham', 'liver', 'pâté', 'squid',
        'clam', 'oyster', 'mussel', 'duck', 'lamb', 'anchovy', 'seafood'
    ]

    text_lower = ingredients_text.lower()
    for keyword in meat_keywords:
        # Check for whole words to avoid false positives (e.g., 'fish' in 'selfish' - unlikely but good practice)
        # Using simple string check for robustness with ingredient lists
        if keyword in text_lower:
            return False

    return True


def main():
    # --- 1. Foody Data Visualization ---
    try:
        print("Processing Foody Data...")
        df_foody = pd.read_csv('foody_data.csv')

        # 1. Clean and Extract District
        df_foody['District'] = df_foody['Location'].apply(extract_district)

        # Filter out "Unknown" or "Other" if they are too few, or keep them.
        # Let's keep only districts with a significant number of restaurants for a cleaner graph
        top_districts = df_foody['District'].value_counts().nlargest(15).index
        df_foody_filtered = df_foody[df_foody['District'].isin(top_districts)]

        # 2. Setup Plot
        plt.figure(figsize=(14, 8))
        sns.set_theme(style="whitegrid")

        # Create a Boxplot: Rating vs District
        # This shows the distribution (min, max, median, quartiles) of ratings for each district
        ax = sns.boxplot(x='District', y='Rating', data=df_foody_filtered, palette="Set3")

        # Add a strip plot on top to show density/individual points if data is sparse,
        # but for distribution, boxplot is sufficient. Let's just style the boxplot.

        plt.title('Distribution of Restaurant Ratings by District (Top 15 Districts)', fontsize=16)
        plt.xlabel('District', fontsize=12)
        plt.ylabel('Rating', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Save
        plt.savefig('foody_district_ratings.svg', format='svg')
        print("Saved: foody_district_ratings.svg")
        plt.close()

    except Exception as e:
        print(f"Error processing Foody data: {e}")

    # --- 2. SavourThePho Data Visualization ---
    try:
        print("Processing SavourThePho Data...")
        df_recipes = pd.read_csv('savourthepho_recipes.csv')

        # 1. Classify Recipes
        df_recipes['Type'] = df_recipes['ingredients'].apply(
            lambda x: 'Vegetarian' if is_vegetarian(x) else 'Non-Vegetarian'
        )

        # 2. Calculate Counts
        counts = df_recipes['Type'].value_counts()

        # 3. Setup Plot
        plt.figure(figsize=(10, 6))

        # Color palette: Green for Veg, Red/Orange for Non-Veg
        colors = ['#ff9999', '#66b3ff']  # Default pastel red/blue
        if 'Vegetarian' in counts.index and 'Non-Vegetarian' in counts.index:
            # Ensure consistent coloring
            colors = ['#2ecc71' if idx == 'Vegetarian' else '#e74c3c' for idx in counts.index]
        elif 'Vegetarian' in counts.index:
            colors = ['#2ecc71']
        else:
            colors = ['#e74c3c']

        # Create Bar Chart
        bars = plt.bar(counts.index, counts.values, color=colors, width=0.6)

        # Add labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2., height,
                     f'{int(height)}',
                     ha='center', va='bottom', fontsize=12, fontweight='bold')

        plt.title('Comparison of Vegetarian vs Non-Vegetarian Recipes', fontsize=16)
        plt.ylabel('Number of Recipes', fontsize=12)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()

        # Save
        plt.savefig('savourthepho_veg_comparison.svg', format='svg')
        print("Saved: savourthepho_veg_comparison.svg")
        plt.close()

    except Exception as e:
        print(f"Error processing SavourThePho data: {e}")


if __name__ == "__main__":
    main()