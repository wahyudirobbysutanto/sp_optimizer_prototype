def analyze_index_fragmentation(connection, database):
    cursor = connection.cursor()
    cursor.execute(f"USE [{database}];")

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
    results = []
    for row in cursor.fetchall():
        frag = row.avg_fragmentation_in_percent
        if frag >= 30:
            action = 'REBUILD'
        elif frag >= 5:
            action = 'REORGANIZE'
        else:
            # action = 'OK'
            continue  # skip yang OK

        results.append({
            'database': database,
            'schema': row.schema_name,
            'table': row.table_name,
            'index': row.index_name,
            'fragmentation': frag,
            'page_count': row.page_count,
            'recommendation': action
        })

    return results

def generate_maintenance_sql(results):
    sql_statements = []
    for row in results:
        if row["recommendation"] in ["REORGANIZE", "REBUILD"]:
            stmt = f"ALTER INDEX [{row['index']}] ON [{row['schema']}].[{row['table']}] {row['recommendation']};"
            sql_statements.append(stmt)
    return "\n".join(sql_statements)

