import os
from datetime import datetime
from difflib import SequenceMatcher
import re

def get_existing_index_info(connection, table_names):
    """
    Mengambil info index yang sudah ada dari daftar tabel (dalam format schema.table).
    """
    if not table_names:
        return ""

    placeholders = []
    for full_table in table_names:
        parts = full_table.split(".")
        if len(parts) == 2:
            schema, table = parts
            placeholders.append(f"(s.name = '{schema}' AND t.name = '{table}')")

    if not placeholders:
        return ""

    where_clause = " OR ".join(placeholders)

    cursor = connection.cursor()
    cursor.execute(f"""
        SELECT 
            s.name AS schema_name,
            t.name AS table_name,
            i.name AS index_name,
            c.name AS column_name
        FROM sys.indexes i
        JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        JOIN sys.tables t ON i.object_id = t.object_id
        JOIN sys.schemas s ON t.schema_id = s.schema_id
        WHERE i.is_primary_key = 0 AND i.is_unique_constraint = 0
        AND ({where_clause})
    """)

    index_lines = []
    for row in cursor.fetchall():
        line = f"{row.schema_name}.{row.table_name}.{row.column_name} --> Indexed as [{row.index_name}]"
        index_lines.append(line)

    return "\n".join(index_lines)


import re

def extract_table_names_from_sql(sql_text):
    """
    Ekstrak nama tabel dari teks SP (dalam format schema.table), termasuk yang memakai [bracket] dan alias.
    """
    # Tangkap nama tabel setelah FROM, JOIN, INTO, UPDATE, DELETE FROM — bisa dalam bentuk [schema].[table]
    pattern = re.compile(
        r"\b(?:FROM|JOIN|INTO|UPDATE|DELETE\s+FROM)\s+(\[?[a-zA-Z0-9_]+\]?\.\[?[a-zA-Z0-9_]+\]?)",
        re.IGNORECASE
    )
    matches = pattern.findall(sql_text)
    
    # Bersihkan dari bracket
    clean_matches = [m.replace("[", "").replace("]", "") for m in matches]
    
    return list(set(clean_matches))



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
