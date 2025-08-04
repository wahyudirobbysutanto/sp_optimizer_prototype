from datetime import datetime
import re
import os
from dotenv import load_dotenv

def extract_sql_only(text):
    """Ambil isi CREATE PROCEDURE dari hasil Gemini (hilangkan penjelasan dan markdown)"""
    # Coba cari blok ```sql ... ```
    match = re.search(r"```sql(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Jika tidak ada blok code, cari langsung CREATE PROCEDURE ... END
    match = re.search(r"(CREATE\s+PROCEDURE\s+.*?END)", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None

def save_sql_to_file(sql_text, filename, folder="outputs"):
    try:
        # Cegah double folder kalau filename sudah ada subfolder
        if not os.path.isabs(filename) and not os.path.dirname(filename):
            os.makedirs(folder, exist_ok=True)
            full_path = os.path.join(folder, filename)
        else:
            full_path = filename
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(sql_text)
        print(f"💾 The SQL is saved to a file: {full_path}")
        return full_path
    except Exception as e:
        print(f"❌ Failed to save to file {filename}:", e)
        return None


def rename_sp_name(sp_sql):
    from datetime import datetime
    import re

    # Gabungkan baris untuk mencari nama SP
    pattern = r"(?i)CREATE\s+PROCEDURE\s+([^\s\(\n]+)"
    match = re.search(pattern, sp_sql.replace('\r', '').replace('\n', ' '))

    if not match:
        raise ValueError("❌ Could not find stored procedure name.")

    original_name = match.group(1).split('.')[-1].strip('[]')
    new_name = f"{original_name}_Opt_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Ganti di string aslinya (tidak usah pakai replace '\n')
    updated_sql = re.sub(
        r"(?i)(CREATE\s+PROCEDURE\s+)([^\s\(\n]+)",
        fr"\1dbo.[{new_name}]",
        sp_sql,
        count=1
    )

    return updated_sql, new_name




def save_optimized_sp(connection, optimized_sql, overwrite=True, db_name=None):    
    
    cursor = connection.cursor()
    try:
        if db_name is None:
            db_name = os.getenv("SQL_DATABASE")

        # Pastikan kita berada di DB yang benar
        cursor.execute(f"USE {db_name};")

        # Eksekusi DROP dulu jika diminta overwrite
        if overwrite:
            drop_stmt = extract_drop_statement(optimized_sql)
            if drop_stmt:
                try:
                    cursor.execute(drop_stmt)
                except Exception as e:
                    print(f"⚠️ Failed to DROP old SP (may not exist yet): {e}")
        
        # Eksekusi SP hasil Gemini
        cursor.execute(optimized_sql)
        connection.commit()
        print(f"✅ SP successfully saved to database '{db_name}'.")
        return True
    except Exception as e:
        print("❌ Failed to save SP optimization results:", e)
        return False


def extract_drop_statement(sp_sql):
    import re
    match = re.search(r'CREATE\s+PROCEDURE\s+(\[?\w+\]?\.)?(\[?\w+\])', sp_sql, re.IGNORECASE)
    if match:
        schema = match.group(1) or 'dbo.'
        name = match.group(2).strip('[]')
        return f"IF OBJECT_ID('{schema}{name}', 'P') IS NOT NULL DROP PROCEDURE {schema}{name};"
    return None
