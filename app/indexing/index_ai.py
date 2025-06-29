from app.gemini_client import ask_gemini
import re

def get_index_recommendation(sp_texts, table_info_text, existing_index_info):
    prompt = f"""Berikan rekomendasi index tambahan berdasarkan isi stored procedure dan struktur tabel berikut. 
Jangan sarankan index yang sudah ada. Format hasil dalam bentuk SQL (CREATE NONCLUSTERED INDEX).

=== STORED PROCEDURES ===
{sp_texts}

=== TABLE STRUCTURE ===
{table_info_text}

=== EXISTING INDEXES ===
{existing_index_info}

Tampilkan hanya index yang **belum ada**, gunakan format nama index: IX_<Table>_<Column>.

    """
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

