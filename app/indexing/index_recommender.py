import os

def get_missing_indexes(connection, db_name=None):
    if not db_name:
        from dotenv import load_dotenv
        load_dotenv()
        db_name = os.getenv("SQL_DATABASE")
        
    try:
        connection.autocommit = True  # penting agar USE db_name bisa jalan
        with connection.cursor() as cursor:
            cursor.execute(f"USE [{db_name}];")
            cursor.execute("""
            SELECT
                DB_NAME(database_id) AS database_name,
                OBJECT_NAME(mid.object_id, database_id) AS table_name,
                mid.equality_columns,
                mid.inequality_columns,
                mid.included_columns,
                migs.unique_compiles,
                migs.user_seeks,
                migs.user_scans,
                migs.avg_total_user_cost,
                migs.avg_user_impact
            FROM sys.dm_db_missing_index_groups mig
            JOIN sys.dm_db_missing_index_group_stats migs ON mig.index_group_handle = migs.group_handle
            JOIN sys.dm_db_missing_index_details mid ON mig.index_handle = mid.index_handle
            ORDER BY migs.user_seeks DESC;
            """)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        print("❌ Gagal mengambil rekomendasi index:", e)
        return []
