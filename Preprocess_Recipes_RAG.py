import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer  # <--- NEW LOCAL IMPORT
import os
import time

# 1. Initialize Local Components
# We DO NOT need Google API here anymore for embeddings.
print("Loading local embedding model... (this happens only once)")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize ChromaDB
client = chromadb.PersistentClient(path="chroma_db")
# Delete old collection if it exists to avoid mixing Google embeddings with Local ones
try:
    client.delete_collection(name="recipes")
except:
    pass
collection = client.create_collection(name="recipes")


def embed_text_locally(text):
    """Helper to get embedding locally"""
    # This runs on your CPU/GPU. No internet needed.
    # .tolist() is important because Chroma expects a list, not a numpy array
    return embedding_model.encode(text).tolist()


def main():
    print("--- Starting Recipe Ingestion (Local Mode) ---")

    # 2. Load Data
    try:
        df = pd.read_csv("savourthepho_recipes.csv")
        df = df.dropna(subset=['name', 'description', 'ingredients'])
        print(f"Loaded {len(df)} recipes.")
    except FileNotFoundError:
        print("Error: savourthepho_recipes.csv not found.")
        return

    # 3. Process & Store
    count = 0

    # We can process in a simple loop. Local models are fast.
    for index, row in df.iterrows():
        combined_text = (
            f"Name: {row['name']}. "
            f"Description: {row['description']}. "
            f"Ingredients: {row['ingredients']}"
        )

        # Get Vector Locally
        vector = embed_text_locally(combined_text)

        collection.add(
            documents=[combined_text],
            embeddings=[vector],
            metadatas=[{"name": row['name']}],
            ids=[str(index)]
        )
        count += 1

        if count % 10 == 0:
            print(f"Processed {count} recipes...")

    print(f"--- Finished! {count} recipes stored in 'chroma_db' folder. ---")


if __name__ == "__main__":
    main()