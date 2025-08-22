from app.utils.utils import get_db_schema_with_indexes_all_databases
from app.db_connector import get_connection

import pyodbc
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle
import os

from dotenv import load_dotenv
load_dotenv(override=True)

DATA_DIR = "data"
FAISS_FILE = os.path.join(DATA_DIR, "faiss_index.bin")
TEXTS_FILE = os.path.join(DATA_DIR, "schema_texts.pkl")
EMBED_FILE = os.path.join(DATA_DIR, "embeddings.npy")

# 3. Convert schema to text
def build_text_from_schema(schema_dict):
    texts = []
    for table, info in schema_dict.items():
        cols = ", ".join(info["columns"])
        idxs = ", ".join(info["indexes"]) if info["indexes"] else "None"
        text = f"{table} ({cols}) Indexes: {idxs}"
        texts.append(text)
    return texts

# 4. Index ke FAISS
def create_faiss_index(texts):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(texts, convert_to_numpy=True)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    return index, embeddings

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)

    with get_connection() as connection:
        schema_dict = get_db_schema_with_indexes_all_databases(connection)
        print(schema_dict)
        texts = build_text_from_schema(schema_dict)

        index, embeddings = create_faiss_index(texts)

        # save FAISS index
        faiss.write_index(index, FAISS_FILE)

        # save schema texts
        with open(TEXTS_FILE, "wb") as f:
            pickle.dump(texts, f)

        # save embeddings (optional)
        np.save(EMBED_FILE, embeddings)

        print("Schema stored in FAISS")
        print("Contoh schema text:", texts[0])
        print("FAISS entries:", index.ntotal)
