import os
import requests
import re
from dotenv import load_dotenv

load_dotenv(override=True)

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
- The result set, logic, and schema (table names, column names, structure) must remain identical.
- You may use any valid T-SQL technique to improve performance, such as:
    - Replacing NOT IN / NOT EXISTS with LEFT JOIN filtering
    - Rewriting or merging CTEs and subqueries
    - Converting correlated subqueries into joins
    - Reordering joins and filters
    - Flattening nested queries if beneficial
- Replace all SELECT * with explicit column lists from the provided table metadata.
- Do not add, remove, or suggest indexes (indexing is handled separately).
- Only use features available in SQL Server Standard Edition.
- Keep the stored procedure name, parameters, and database/schema references exactly the same.
- Do not modify or remove any existing comments inside the stored procedure.
- Ignore any remarks section for optimization — do not change its text.
- Do not output explanations or reasoning — only the final optimized stored procedure.
- Do not add or remove parameters.
- Only change SQL if it improves execution performance without altering the output.

**Strict output format:**
Return only the optimized stored procedure, wrapped between the tags below.

=== SP_OPTIMIZED ===  
(optimized code here)
"""
#     prompt = f"""
# You are a SQL Server expert. Your task is to optimize the following stored procedure for performance and clarity.

# Below is the current stored procedure:

# === BEGIN SP ===
# {sp_text}
# === END SP ===

# And here is the list of related tables, including their columns and existing indexes:

# === BEGIN TABLE INFO ===
# {table_info_text}
# === END TABLE INFO ===


# Your optimization must meet **all** of the following conditions:
# - Do not change the result or schema (column names, table names, structure)
# - Replace all SELECT * with explicit column lists based on the table metadata
# - Reorder JOINs or filters if that improves performance, but maintain logic
# - Do not suggest or add indexes — indexing is handled in another step
# - Do not use features unavailable in SQL Server Standard Edition
# - Final output must be a single valid stored procedure that can be run as-is
# - ignore the remarks in the stored procedure, focus on the SQL logic
# - Do not include any comments or explanations in the output
# - Do not change the stored procedure name or parameters
# - Do not change the database name or schema
# - Do not change anything inside the remarks section of the stored procedure
# - Do not remove any existing comments in the stored procedure
# - Change the logic only if it improves performance without altering the output

# **Strict output format:**
# Return only the optimized stored procedure, wrapped between the tags below.

# === SP_OPTIMIZED ===  
# (optimized code here)
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

    # print(prompt)
    try:
        response = requests.post(
            GEMINI_URL + f"?key={GEMINI_API_KEY}",
            headers=headers,
            json=body,
            timeout=600
        )
        response.raise_for_status()
        content = response.json()
        return content["candidates"][0]["content"]["parts"][0]["text"]
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error from Gemini: {e}")
    except Exception as e:
        print(f"❌ Other error from Gemini: {e}")
    
    return None
