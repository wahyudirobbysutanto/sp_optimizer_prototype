import sqlparse

def execute_sql_statements(connection, sql_text):
    cursor = connection.cursor()
    statements = sqlparse.split(sql_text.strip())

    for stmt in statements:
        clean_stmt = stmt.strip()
        if not clean_stmt:
            continue
        try:
            cursor.execute(clean_stmt)
        except Exception as e:
            print(f"❌ Gagal menjalankan:\n{clean_stmt}\n🔺Error: {e}")
    connection.commit()
