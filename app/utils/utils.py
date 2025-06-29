import os
from datetime import datetime
from difflib import SequenceMatcher

def is_similar_sql(original_sql, optimized_sql, threshold=0.95):
    matcher = SequenceMatcher(None, original_sql.lower(), optimized_sql.lower())
    similarity = matcher.ratio()
    return similarity >= threshold, similarity

def timestamp_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def log_result(sp_name, status, similarity=None, note=None):
    os.makedirs("logs", exist_ok=True)
    with open("logs/optimization_log.txt", "a", encoding="utf-8") as f:
        line = f"{timestamp_str()} | {sp_name} | {status}"
        if similarity:
            line += f" | Similarity: {round(similarity, 4)}"
        if note:
            line += f" | Note: {note}"
        f.write(line + "\n")

def log_to_sql(connection, sp_name, status, similarity=None, note=None):
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO OptimizationLog (SPName, Status, Similarity, Note)
            VALUES (?, ?, ?, ?)
        """, (sp_name, status, similarity, note))
        connection.commit()
    except Exception as e:
        print(f"⚠️ Gagal log ke database: {e}")
