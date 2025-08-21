import pyodbc
import re

def get_slow_sp(connection):
    cursor = connection.cursor()

    # This DMV is instance-wide, so we don't need to change databases
    # We just filter to user databases and stored procs
    query = """
        SELECT 
            DB_NAME(st.dbid) AS database_name,
            OBJECT_NAME(st.objectid, st.dbid) AS object_name,
            qs.total_worker_time / qs.execution_count AS avg_cpu_time,
            qs.total_elapsed_time / qs.execution_count AS avg_elapsed_time,
            qs.execution_count,
            qs.total_elapsed_time,
            qs.creation_time,
            st.text AS sql_text
        FROM sys.dm_exec_query_stats qs
        CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
        WHERE st.objectid IS NOT NULL
        AND OBJECT_NAME(st.objectid, st.dbid) IS NOT NULL
        AND DB_NAME(st.dbid) NOT IN ('master', 'msdb', 'tempdb', 'model')
        ORDER BY avg_elapsed_time DESC
    """

    cursor.execute(query)
    results = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in results]


# def get_slow_sp(connection):
#     cursor = connection.cursor()
#     cursor.execute("""
#         SELECT TOP 50 
#             DB_NAME(st.dbid) AS database_name,
#             OBJECT_NAME(st.objectid, st.dbid) AS object_name,
#             qs.total_worker_time / qs.execution_count AS avg_cpu_time,
#             qs.total_elapsed_time / qs.execution_count AS avg_elapsed_time,
#             qs.execution_count,
#             qs.total_elapsed_time,
#             qs.creation_time,
#             st.text AS sql_text
#         FROM sys.dm_exec_query_stats qs
#         CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
#         WHERE st.objectid IS NOT NULL
#         ORDER BY avg_elapsed_time DESC
#     """)
#     results = cursor.fetchall()
#     columns = [desc[0] for desc in cursor.description]
#     return [dict(zip(columns, row)) for row in results]


def get_all_databases(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sys.databases WHERE database_id > 4")  # skip system DBs
    return [row.name for row in cursor.fetchall()]

def get_sp_definition(connection, db_name, schema, name):
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(f"USE [{db_name}];")
            cursor.execute("""
                SELECT sm.definition
                FROM sys.sql_modules sm
                INNER JOIN sys.objects o ON sm.object_id = o.object_id
                INNER JOIN sys.schemas s ON o.schema_id = s.schema_id
                WHERE s.name = ? AND o.name = ?;
            """, (schema, name))
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        print("❌ Gagal mengambil isi SP:", e)
        return None


def get_stored_procedures_all_databases(connection):
    cursor = connection.cursor()

    # Step 1: Get all user databases
    cursor.execute("""
        SELECT name
        FROM sys.databases
        WHERE name NOT IN ('master','model','msdb','tempdb')
    """)
    db_list = [row.name for row in cursor.fetchall()]

    all_procs = []

    # Step 2: Loop through each DB and collect stored procedures
    for db in db_list:
        cursor.execute(f"USE [{db}];")
        cursor.execute("""
            SELECT 
                SCHEMA_NAME(schema_id) AS schema_name,
                name,
                OBJECT_DEFINITION(object_id) AS definition,
                OBJECTPROPERTY(object_id, 'IsEncrypted') AS is_encrypted
            FROM sys.objects
            WHERE type = 'P'
        """)
        for row in cursor.fetchall():
            all_procs.append({
                "database": db,
                "schema": row.schema_name,
                "name": row.name,
                "definition": row.definition,
                "is_encrypted": row.is_encrypted,
                "full_name": f"{db}.{row.schema_name}.{row.name}"
            })

    return all_procs


def get_stored_procedures(connection, database):
    cursor = connection.cursor()
    cursor.execute(f"USE [{database}];")
    cursor.execute("""
        SELECT 
            SCHEMA_NAME(schema_id) AS schema_name,
            name,
            OBJECT_DEFINITION(object_id) AS definition,
            OBJECTPROPERTY(object_id, 'IsEncrypted') AS is_encrypted
        FROM sys.objects
        WHERE type = 'P'
    """)
    return [{
        'schema': row.schema_name,
        'name': row.name,
        'definition': row.definition,
        'is_encrypted': row.is_encrypted,
        'database': database
    } for row in cursor.fetchall()]

def get_tables(connection, database):
    cursor = connection.cursor()
    cursor.execute(f"USE [{database}];")
    cursor.execute("""
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
    """)
    return [{
        'schema': row.TABLE_SCHEMA,
        'table': row.TABLE_NAME,
        'database': database
    } for row in cursor.fetchall()]

def get_table_columns(connection, db_name, schema, table, sp_text=None):
    with connection.cursor() as cursor:
        cursor.execute(f"USE {db_name};")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """, (schema, table))
        all_columns = cursor.fetchall()

        used_cols = []
        for col, dtype in all_columns:
            # cari pola "table.col" atau langsung "col"
            pattern1 = rf"\b{table}\s*\.\s*{col}\b"
            pattern2 = rf"\b{col}\b"
            if re.search(pattern1, sp_text, re.IGNORECASE) or re.search(pattern2, sp_text, re.IGNORECASE):
                used_cols.append(f"{col} ({dtype})")

        # fallback: kalau tidak ketemu sama sekali, pakai semua
        if not used_cols:
            used_cols = [f"{col} ({dtype})" for col, dtype in all_columns]

        return used_cols

        # return [f"{row[0]} ({row[1]})" for row in cursor.fetchall()]

def get_table_indexes(connection, db, schema, table):
    sql = f"""
    SELECT 
        ind.name AS index_name,
        ind.type_desc AS index_type,
        col.name AS column_name,
        ic.is_included_column
    FROM {db}.sys.indexes ind
    JOIN {db}.sys.index_columns ic
        ON ind.object_id = ic.object_id AND ind.index_id = ic.index_id
    JOIN {db}.sys.columns col
        ON ic.object_id = col.object_id AND ic.column_id = col.column_id
    WHERE ind.object_id = OBJECT_ID('{db}.{schema}.{table}')
    ORDER BY ind.name, ic.key_ordinal;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    return rows


def build_detailed_table_info(connection, db_name, tables):
    """tables: list of tuples like (schema, table)"""
    lines = []
    for schema, table in tables:
        cols = get_table_columns(connection, db_name, schema, table)
        col_list = ", ".join(cols)
        lines.append(f"{schema}.{table} ({col_list})")
    return "\n".join(lines)
