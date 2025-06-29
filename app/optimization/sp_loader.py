import pyodbc

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


def get_table_columns(connection, db_name, schema, table):
    with connection.cursor() as cursor:
        # Jalankan USE DB dulu sebagai perintah terpisah
        cursor.execute(f"USE {db_name};")

        # Lanjutkan query SELECT kolom
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """, (schema, table))

        return [row[0] for row in cursor.fetchall()]


def build_detailed_table_info(connection, db_name, tables):
    """tables: list of tuples like (schema, table)"""
    lines = []
    for schema, table in tables:
        cols = get_table_columns(connection, db_name, schema, table)
        col_list = ", ".join(cols)
        lines.append(f"{schema}.{table} ({col_list})")
    return "\n".join(lines)
