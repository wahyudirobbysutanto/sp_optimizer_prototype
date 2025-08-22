import os
import requests
import re
from dotenv import load_dotenv
from app.gemini_client import ask_gemini

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
You are a SQL Server expert. Your task is to **rewrite and optimize** the following stored procedure for performance and clarity.

**Input:**
1. Current stored procedure:

=== BEGIN SP ===
{sp_text}
=== END SP ===

2. Related tables (columns + existing indexes):

=== BEGIN TABLE INFO ===
{table_info_text}
=== END TABLE INFO ===


**Optimization rules:**
- **Keep output identical**: Result set, logic, and schema (table names, column names, and structure) must not change.
- **Parameter handling**: At the very start of the procedure, assign each incoming parameter to a local variable of the same data type, and use that variable in queries to avoid parameter sniffing.
- **Allowed optimizations** (only if they improve performance without changing output):
  - Replace `NOT IN` / `NOT EXISTS` with `LEFT JOIN` filtering if faster.
  - Convert correlated subqueries to joins.
  - Reorder joins and filters for better performance.
  - Flatten nested queries where beneficial.
- Replace all `SELECT *` with **explicit column lists** based on provided table metadata.
- Do **not**:
  - Add, remove, or suggest indexes.
  - Change stored procedure name, parameters, database, or schema references.
  - Modify or remove any existing comments inside the procedure.
  - Change the `UNION` / `UNION ALL` usage — keep exactly as in the original. This is a hard constraint.  
  - Convert `UNION` to `UNION ALL` or `UNION ALL` to `UNION` under any circumstances.
  - Add explanations or reasoning — output only the final code.
  - Add or remove parameters.
- Only use features available in **SQL Server Standard Edition**.
- **Strict SQL Server compatibility rules**:
  - Do not use `MAX(a, b)`, `MIN(a, b)`, `GREATEST()`, `LEAST()`, or any non-T-SQL scalar functions.
  - To compare scalar values, use `CASE WHEN ... THEN ... ELSE ... END` or `IIF()` (SQL Server 2012+).
  - Do not generate PL/pgSQL, PL/SQL, or MySQL syntax (no `LIMIT`, no `:=`, no `ON DUPLICATE KEY`, etc.).
  - Use only T-SQL syntax supported by SQL Server.
- Ignore any remarks section for optimization — keep it unchanged.

**Output format (strict)**:

=== SP_OPTIMIZED ===  
(optimized code here)  
=== END SP_OPTIMIZED ===

    """
    
    

#     prompt = f"""
# You are a SQL Server expert. Your task is to **rewrite and optimize** the following stored procedure for performance and clarity.

# **Input:**
# 1. Current stored procedure:

# === BEGIN SP ===
# {sp_text}
# === END SP ===

# 2. Related tables (columns + existing indexes):

# === BEGIN TABLE INFO ===
# {table_info_text}
# === END TABLE INFO ===


# **Optimization rules:**
# - **Keep output identical**: Result set, logic, and schema (table names, column names, and structure) must not change.
# - **Parameter handling**: At the very start of the procedure, assign each incoming parameter to a local variable of the same data type, and use that variable in queries to avoid parameter sniffing.
# - **Allowed optimizations** (only if they improve performance without changing output):
#   - Replace `NOT IN` / `NOT EXISTS` with `LEFT JOIN` filtering if faster.
#   - Convert correlated subqueries to joins.
#   - Reorder joins and filters for better performance.
#   - Flatten nested queries where beneficial.
# - Replace all `SELECT *` with **explicit column lists** based on provided table metadata.
# - Do **not**:
#   - Add, remove, or suggest indexes.
#   - Change stored procedure name, parameters, database, or schema references.
#   - Modify or remove any existing comments inside the procedure.
#   - Change the `UNION` / `UNION ALL` usage — keep exactly as in the original. This is a hard constraint.  
#   - Convert `UNION` to `UNION ALL` or `UNION ALL` to `UNION` under any circumstances.
#   - Add explanations or reasoning — output only the final code.
#   - Add or remove parameters.
# - Only use features available in **SQL Server Standard Edition**.
# - Ignore any remarks section for optimization — keep it unchanged.

# **Output format (strict)**:

# === SP_OPTIMIZED ===  
# (optimized code here)  
# === END SP_OPTIMIZED ===

#     """
    
    # prompt = f"""
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
# - The result set, logic, and schema (table names, column names, structure) must remain identical.
# - Always assign each incoming parameter to a local variable at the start of the procedure, and use the local variable in queries instead of the raw parameter. This is to avoid parameter sniffing and keep execution plans stable across executions with different parameter values.
# - You may use any valid T-SQL technique to improve performance, such as:
    # - Replacing NOT IN / NOT EXISTS with LEFT JOIN filtering where beneficial
    # - Converting correlated subqueries into joins
    # - Reordering joins and filters
    # - Flattening nested queries if beneficial
# - Replace all SELECT * with explicit column lists from the provided table metadata.
# - Do not add, remove, or suggest indexes (indexing is handled separately).
# - Only use features available in SQL Server Standard Edition.
# - Keep the stored procedure name, parameters, and database/schema references exactly the same.
# - Do not modify or remove any existing comments inside the stored procedure.
# - Ignore any remarks section for optimization — do not change its text.
# - Do not output explanations or reasoning — only the final optimized stored procedure.
# - Do not add or remove parameters.
# - Only change SQL if it improves execution performance without altering the output.
# - Do not change the UNION with UNION ALL. 

# **Strict output format:**
# Return only the optimized stored procedure, wrapped between the tags below.

# === SP_OPTIMIZED ===  
# (optimized code here)
# === END SP_OPTIMIZED ===
# """

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
# - Always assign each incoming parameter to a local variable at the start of the procedure, and use the local variable in queries instead of the raw parameter. This is to avoid parameter sniffing and keep execution plans stable across executions with different parameter values.
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
# === END SP_OPTIMIZED ===
# """



    # headers = {
    #     "Content-Type": "application/json"
    # }

    # body = {
    #     "contents": [
    #         {
    #             "parts": [
    #                 {"text": prompt}
    #             ]
    #         }
    #     ],
    #     "generationConfig": {
    #         "temperature": 0,
    #         "topK": 1,
    #         "topP": 0.1
    #     }
    # }

    # print(prompt)
    try:
        # response = requests.post(
        #     GEMINI_URL + f"?key={GEMINI_API_KEY}",
        #     headers=headers,
        #     json=body,
        #     timeout=600
        # )
        # print(f"Response status code: {response}")
        # response.raise_for_status()
        # content = response.json()
        # print(content)
        response = ask_gemini(prompt)
        return response
        # return content["candidates"][0]["content"]["parts"][0]["text"]
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error from Gemini: {e}")
    except Exception as e:
        print(f"❌ Other error from Gemini: {e}")
    
    return None
