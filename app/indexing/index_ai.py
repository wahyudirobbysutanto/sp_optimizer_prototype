from app.gemini_client import ask_gemini
import re

def get_index_recommendation(sp_texts, table_info_text):
    prompt = f"""You are a SQL performance tuning expert.

Analyze the stored procedures and table definitions below. Recommend only additional NONCLUSTERED indexes that will significantly improve SELECT, JOIN, and ORDER BY performance.

Rules:
1. Only suggest indexes if the column(s) appear in WHERE, JOIN, or ORDER BY clauses.
2. Do NOT suggest indexes if the column is already indexed (clustered or non-clustered).
3. Avoid suggesting indexes on columns with low selectivity (e.g., boolean flags, tiny lookup codes) unless combined with another column in a composite index.
4. Avoid suggesting indexes on columns that are frequently updated unless the read performance gain is clearly worth the write cost.
5. Use composite (multi-column) indexes only if they are clearly needed for the query pattern.
6. Output only the CREATE INDEX statements, using this format:

CREATE INDEX IX_<Table>_<Column> ON [<DatabaseName>].[<SchemaName>].[<TableName>] (<Column>);

=== STORED PROCEDURES ===
{sp_texts}

=== TABLE STRUCTURE & INDEX ===
{table_info_text}

"""

    print(prompt)
#     prompt = f"""
# Saya sedang membangun sistem analisis index untuk SQL Server.

# Berikut adalah definisi stored procedure yang akan dianalisis:

# === BEGIN SP ===
# {sp_text}
# === END SP ===

# Berikut informasi tabel-tabel yang digunakan:

# === BEGIN TABLE INFO ===
# {table_info_text}
# === END TABLE INFO ===

# Tolong:
# - Identifikasi kolom mana yang digunakan dalam WHERE, JOIN, GROUP BY, ORDER BY
# - Jika kolom tersebut belum memiliki index, rekomendasikan CREATE INDEX.
# - Jika sudah ada index, tuliskan bahwa index tersebut sudah ada.
# - Sertakan analisa singkat per kolom.

# Hanya berikan:
# 1. === INDEX_RECOMMENDATION === (DDL per kolom)
# 2. === ALASAN === (analisa singkat)
# """

    response = ask_gemini(prompt)
    # print("AI Response:", response)
    return extract_index_ddl(response)

def extract_index_ddl(ai_text):
    """
    Ekstrak semua perintah CREATE INDEX dari teks AI.
    Mendeteksi berbagai variasi, seperti NONCLUSTERED, UNIQUE, dan komentar SQL.
    """
    pattern = re.compile(r"CREATE\s+(?:NONCLUSTERED\s+|UNIQUE\s+)?INDEX\s+[\[\]A-Za-z0-9_]+.*?ON\s+[\[\]A-Za-z0-9_.]+\s*\([^)]+\);", re.IGNORECASE | re.DOTALL)
    matches = pattern.findall(ai_text)
    return "\n".join([m.strip() for m in matches])

