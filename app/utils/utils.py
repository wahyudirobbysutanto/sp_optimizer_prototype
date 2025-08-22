import os
from datetime import datetime
from difflib import SequenceMatcher
import re

import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

# --- Tambahan untuk FAISS ---
DATA_DIR = "data"
FAISS_FILE = os.path.join(DATA_DIR, "faiss_index.bin")
TEXTS_FILE = os.path.join(DATA_DIR, "schema_texts.pkl")

# Load model & index sekali
_model = None
_index = None
_texts = None

def load_faiss():
    global _model, _index, _texts
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    if _index is None:
        _index = faiss.read_index(FAISS_FILE)
    if _texts is None:
        with open(TEXTS_FILE, "rb") as f:
            _texts = pickle.load(f)
    return _model, _index, _texts

def search_schema(query, top_k=5):
    """Cari schema relevan di FAISS"""
    model, index, texts = load_faiss()
    q_emb = model.encode([query], convert_to_numpy=True)
    D, I = index.search(q_emb, top_k)
    results = [(texts[i], float(D[0][j])) for j, i in enumerate(I[0])]
    return results

def get_existing_index_info(connection, table_names):
    """
    Get index info from a list of db.schema.table names.
    Returns a string with indexes grouped by table.
    """
    from collections import defaultdict

    if not table_names:
        return ""

    # Group tables by database
    grouped = defaultdict(list)
    for full_table in table_names:
        parts = full_table.split(".")
        if len(parts) == 3:
            db, schema, table = parts
            grouped[db].append((schema, table))

    index_lines = []

    cursor = connection.cursor()
    for db, tables in grouped.items():
        # Build WHERE clause for this database
        table_clauses = [f"(s.name = '{schema}' AND t.name = '{table}')" for schema, table in tables]
        where_clause = " OR ".join(table_clauses)

        # Switch database
        cursor.execute(f"USE [{db}];")

        query = f"""
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
            ORDER BY s.name, t.name, i.name, ic.key_ordinal;
        """
        cursor.execute(query)

        for row in cursor.fetchall():
            index_lines.append(
                f"{db}.{row.schema_name}.{row.table_name}.{row.column_name} --> Indexed as [{row.index_name}]"
            )

    return "\n".join(index_lines)

def extract_table_names_from_sql_new(sql_text, default_db=None):
    """
    Extract table names from SQL text, returning full identifiers:
    db.schema.table
    Removes comments first so patterns in comments are ignored.
    Excludes temporary tables (#temp, ##globaltemp).
    """

    # Remove multi-line comments (/* ... */)
    sql_no_multiline = re.sub(r"/\*.*?\*/", "", sql_text, flags=re.DOTALL)

    # Remove single-line comments (-- ...)
    sql_no_comments = re.sub(r"--.*?$", "", sql_no_multiline, flags=re.MULTILINE)

    # Capture table references, but exclude temp tables starting with #
    pattern = re.compile(
        r"""
        \b(?:FROM|JOIN|INTO|UPDATE|DELETE\s+FROM)\s+
        (?!\#)                                 # exclude temp tables
        (
            (?:\[?[a-zA-Z0-9_]+\]?\.){0,2}     # 0 to 2 prefixes (db. schema.)
            \[?[a-zA-Z0-9_]+\]?                # final object
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    matches = pattern.findall(sql_no_comments)
    cleaned = []

    for m in matches:
        # Skip temp tables again as extra safety
        if m.strip().startswith("#"):
            continue

        parts = [p for p in m.replace("[", "").replace("]", "").split(".") if p]
        if len(parts) == 1 and default_db:
            full_name = f"{default_db}.dbo.{parts[0]}"
        elif len(parts) == 2 and default_db:
            full_name = f"{default_db}.{parts[0]}.{parts[1]}"
        else:
            full_name = ".".join(parts)
        cleaned.append(full_name)

    return list(set(cleaned))



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
        print(f"⚠️ Failed to log into database: {e}")


def get_db_schema_with_indexes_all_databases(connection):
    cursor = connection.cursor()

    # ambil semua database kecuali system
    cursor.execute("""
        SELECT name 
        FROM sys.databases
        WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb')
    """)
    databases = [row[0] for row in cursor.fetchall()]

    all_schema_info = {}

    for db in databases:
        try:
            print(f"🔍 Processing database: {db}")
            cursor.execute(f"USE [{db}]")

            query = """
            SELECT 
                sch.name AS SchemaName,
                t.name AS TableName,
                c.name AS ColumnName,
                ty.name AS DataType,
                i.name AS IndexName,
                i.type_desc AS IndexType,
                ic.is_included_column,
                ic.key_ordinal
            FROM sys.tables t
            INNER JOIN sys.schemas sch ON t.schema_id = sch.schema_id
            INNER JOIN sys.columns c ON t.object_id = c.object_id
            INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
            LEFT JOIN sys.index_columns ic 
                ON t.object_id = ic.object_id AND c.column_id = ic.column_id
            LEFT JOIN sys.indexes i 
                ON ic.object_id = i.object_id AND ic.index_id = i.index_id
            ORDER BY sch.name, t.name, i.name, ic.key_ordinal;
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            schema_info = {}
            for row in rows:
                table_key = f"{db}.{row.SchemaName}.{row.TableName}"
                if table_key not in schema_info:
                    schema_info[table_key] = {
                        "columns": [],
                        "indexes": {}
                    }
                schema_info[table_key]["columns"].append(f"{row.ColumnName} ({row.DataType})")

                if row.IndexName:
                    if row.IndexName not in schema_info[table_key]["indexes"]:
                        schema_info[table_key]["indexes"][row.IndexName] = {
                            "type": row.IndexType,
                            "columns": []
                        }
                    schema_info[table_key]["indexes"][row.IndexName]["columns"].append(row.ColumnName)

            all_schema_info.update(schema_info)

        except Exception as e:
            print(f"⚠️ Skipping database {db}: {e}")

    return all_schema_info



