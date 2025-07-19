from app.gemini_client import ask_gemini
import re

def get_index_recommendation(sp_texts, table_info_text, existing_index_info):
    prompt = f"""You are a SQL performance tuning expert.

Please analyze the stored procedure and table definitions below. Recommend additional non-clustered indexes to improve query performance. Focus on WHERE, JOIN, and ORDER BY clauses.

Only suggest indexes that are not already present.

Output only the SQL commands to create the suggested indexes, using this naming convention: IX_<Table>_<Column>. Use one index per column (no multi-column indexes unless absolutely necessary).

=== STORED PROCEDURES ===
{sp_texts}

=== TABLE STRUCTURE ===
{table_info_text}

=== EXISTING INDEXES ===
{existing_index_info}
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
    return extract_index_ddl(response)

def extract_index_ddl(ai_text):
    """
    Ekstrak semua perintah CREATE INDEX dari teks AI.
    Mendeteksi berbagai variasi, seperti NONCLUSTERED, UNIQUE, dan komentar SQL.
    """
    pattern = re.compile(r"CREATE\s+(?:NONCLUSTERED\s+|UNIQUE\s+)?INDEX\s+[\[\]A-Za-z0-9_]+.*?ON\s+[\[\]A-Za-z0-9_.]+\s*\([^)]+\);", re.IGNORECASE | re.DOTALL)
    matches = pattern.findall(ai_text)
    return "\n".join([m.strip() for m in matches])

