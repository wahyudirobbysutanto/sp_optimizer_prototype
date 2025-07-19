import os
import requests
import re
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


def sanitize_sql(generated_sql):
    lines = generated_sql.strip().splitlines()
    start_idx = 0

    # Cari baris pertama yang mengandung CREATE PROCEDURE
    for i, line in enumerate(lines):
        if re.search(r'\bCREATE\s+PROCEDURE\b', line, re.IGNORECASE):
            start_idx = i
            break

    cleaned_lines = lines[start_idx:]
    cleaned_text = "\n".join(cleaned_lines)

    # Hapus karakter tidak valid
    cleaned_text = cleaned_text.replace("`", "")
    cleaned_text = re.sub(r"^\s*\d+\.\s*", "", cleaned_text, flags=re.MULTILINE)

    return cleaned_text

def optimize_stored_procedure(sp_text, table_info_text=None):
    if table_info_text is None:
        table_info_text = "(tidak ada metadata tabel)"
    
    prompt = f"""
You are a SQL Server expert. Your task is to optimize the following stored procedure for performance and clarity.

Below is the current stored procedure:

=== BEGIN SP ===
{sp_text}
=== END SP ===

And here is the list of related tables, including their columns and existing indexes:

=== BEGIN TABLE INFO ===
{table_info_text}
=== END TABLE INFO ===


Your optimization must meet **all** of the following conditions:
- Do not change the result or schema (column names, table names, structure)
- Replace all SELECT * with explicit column lists based on the table metadata
- Reorder JOINs or filters if that improves performance, but maintain logic
- Do not suggest or add indexes — indexing is handled in another step
- Do not use features unavailable in SQL Server Standard Edition
- Final output must be a single valid stored procedure that can be run as-is

**Strict output format:**
Return only the optimized stored procedure, wrapped between the tags below.

=== SP_OPTIMIZED ===  
(optimized code here)
"""
#     prompt = f"""
# Saya sedang membangun sistem otomatis untuk optimasi stored procedure SQL Server.

# Berikut adalah definisi stored procedure yang ingin dioptimalkan:

# === BEGIN SP ===
# {sp_text}
# === END SP ===

# Berikut informasi tabel-tabel yang digunakan, termasuk kolom dan index yang sudah ada:

# === BEGIN TABLE INFO ===
# {table_info_text}
# === END TABLE INFO ===

# Tolong optimalkan stored procedure tersebut agar lebih efisien, **tanpa mengubah hasil akhir atau struktur tabel/schema**.

# Instruksi penting:
# - Gantilah semua SELECT * dengan daftar kolom eksplisit dari metadata di atas
# - Jangan ubah nama tabel atau kolom
# - Hindari fitur yang tidak tersedia di SQL Server Standard Edition
# - Jika bisa, sertakan juga saran index baru yang relevan (jika belum ada)
# - Hasil akhir harus bisa langsung dijalankan di SQL Server

# **Format jawaban wajib**:
# 1. === PENJELASAN ===  
# (Singkat dan to the point)

# 2. === SP_OPTIMIZED ===  
# (Stored procedure versi baru)

# 3. === INDEX_RECOMMENDATION ===  
# (List atau DDL dari index tambahan jika diperlukan)

# Hanya jawab sesuai format di atas. Jangan beri narasi tambahan di luar 3 bagian itu.
# """


    headers = {
        "Content-Type": "application/json"
    }

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(
            GEMINI_URL + f"?key={GEMINI_API_KEY}",
            headers=headers,
            json=body,
            timeout=30
        )
        response.raise_for_status()
        content = response.json()
        return content["candidates"][0]["content"]["parts"][0]["text"]
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error from Gemini: {e}")
    except Exception as e:
        print(f"❌ Other error from Gemini: {e}")
    
    return None
