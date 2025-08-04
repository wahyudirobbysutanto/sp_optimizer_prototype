import os
from datetime import datetime
from difflib import SequenceMatcher
import re

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



import re


def extract_table_names_from_sql_new(sql_text, default_db=None):
    """
    Extract table names from SQL text, returning full identifiers:
    db.schema.table
    Removes comments first so patterns in comments are ignored.
    """

    # Remove multi-line comments (/* ... */)
    sql_no_multiline = re.sub(r"/\*.*?\*/", "", sql_text, flags=re.DOTALL)

    # Remove single-line comments (-- ...)
    sql_no_comments = re.sub(r"--.*?$", "", sql_no_multiline, flags=re.MULTILINE)

    # Capture table references
    pattern = re.compile(
        r"""
        \b(?:FROM|JOIN|INTO|UPDATE|DELETE\s+FROM)\s+
        (
            (?:\[?[a-zA-Z0-9_]+\]?\.){0,2}      # 0 to 2 prefixes (db. schema.)
            \[?[a-zA-Z0-9_]+\]?                 # final object
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    matches = pattern.findall(sql_no_comments)
    cleaned = []

    for m in matches:
        parts = [p for p in m.replace("[", "").replace("]", "").split(".") if p]
        if len(parts) == 1 and default_db:
            # Only table: assume dbo schema and add db
            full_name = f"{default_db}.dbo.{parts[0]}"
        elif len(parts) == 2 and default_db:
            # schema.table: add db
            full_name = f"{default_db}.{parts[0]}.{parts[1]}"
        else:
            # Already db.schema.table
            full_name = ".".join(parts)
        cleaned.append(full_name)

    return list(set(cleaned))



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
        print(f"⚠️ Failed to log into database: {e}")
