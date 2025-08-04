from app.indexing.fragmentation_analyzer import generate_maintenance_sql
from app.indexing.index_ai import get_index_recommendation
from app.optimization.sp_loader import get_stored_procedures, get_sp_definition, get_tables, get_table_columns

def generate_recommendation_procedure(connection, database):
    # 1. Dapatkan SQL Rebuild/Reorganize
    frag_results = analyze_index_fragmentation_all(connection)
    maintenance_sql = generate_maintenance_sql(frag_results)

    # 2. Ambil semua SP dan info tabel
    sps = get_stored_procedures(connection, database)
    sps = [sp for sp in sps if not sp["is_encrypted"]]

    all_sql = []
    for sp in sps:
        sp_def = get_sp_definition(connection, database, sp["schema"], sp["name"])
        if not sp_def:
            continue

        tables = get_tables(connection, database)
        table_info_lines = []
        for tbl in tables:
            cols = get_table_columns(connection, database, tbl["schema"], tbl["table"])
            line = f"{tbl['schema']}.{tbl['table']} ({', '.join(cols)})"
            table_info_lines.append(line)
        table_info_text = "\n".join(table_info_lines)

        ai_response = get_index_recommendation(sp_def, table_info_text)
        if "=== INDEX_RECOMMENDATION ===" in ai_response:
            rec_section = ai_response.split("=== INDEX_RECOMMENDATION ===")[1]
            rec_sql = rec_section.split("===")[0].strip()
            all_sql.append(rec_sql)

    all_sql_combined = maintenance_sql.strip() + "\n\n-- AI Suggested Indexes --\n" + "\n".join(all_sql)

    # 3. Bungkus jadi SP
    full_procedure = f"""
    USE TestDB
    GO

DROP PROCEDURE IF EXISTS recommendation_index;
GO

CREATE PROCEDURE recommendation_index
AS
BEGIN
{indent_sql_block(all_sql_combined)}
END
"""
    return full_procedure.strip()

def indent_sql_block(sql):
    lines = sql.splitlines()
    return "\n".join("    " + line for line in lines)
