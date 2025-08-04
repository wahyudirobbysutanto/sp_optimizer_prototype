
def analyze_index_fragmentation_all(connection):
    cursor = connection.cursor()
    # Get list of databases
    cursor.execute("""
        SELECT name 
        FROM sys.databases
        WHERE database_id > 4  -- skip master, tempdb, model, msdb
    """)
    databases = [row[0] for row in cursor.fetchall()]

    all_results = []

    for db in databases:
        try:
            cursor.execute(f"USE [{db}];")

            query = """
            SELECT 
                s.name AS schema_name,
                t.name AS table_name,
                i.name AS index_name,
                ps.index_type_desc,
                ps.avg_fragmentation_in_percent,
                ps.page_count
            FROM sys.dm_db_index_physical_stats (DB_ID(), NULL, NULL, NULL, 'LIMITED') AS ps
            JOIN sys.indexes i ON ps.object_id = i.object_id AND ps.index_id = i.index_id
            JOIN sys.tables t ON i.object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE ps.database_id = DB_ID()
              AND ps.page_count > 100
              AND i.name IS NOT NULL
            ORDER BY ps.avg_fragmentation_in_percent DESC;
            """

            cursor.execute(query)
            for row in cursor.fetchall():
                frag = row.avg_fragmentation_in_percent
                if frag >= 30:
                    action = "REBUILD"
                elif frag >= 5:
                    action = "REORGANIZE"
                else:
                    continue  # skip low fragmentation

                all_results.append({
                    "database": db,
                    "schema": row.schema_name,
                    "table": row.table_name,
                    "index": row.index_name,
                    "fragmentation": frag,
                    "page_count": row.page_count,
                    "recommendation": action,
                })
        except Exception as e:
            print(f"Failed to analyze {db}: {e}")

    return all_results


def generate_maintenance_sql(results):
    sql_statements = []
    for row in results:
        if row["recommendation"] in ["REORGANIZE", "REBUILD"]:
            stmt = f"ALTER INDEX [{row['index']}] ON [{row['database']}].[{row['schema']}].[{row['table']}] {row['recommendation']};"
            sql_statements.append(stmt)
    return "\n".join(sql_statements)

