import pyodbc

def get_unused_indexes_all_databases(connection):
    cursor = connection.cursor()

    # Step 1: Get all user databases
    cursor.execute("""
        SELECT name
        FROM sys.databases
        WHERE name NOT IN ('master','model','msdb','tempdb')
    """)
    db_list = [row.name for row in cursor.fetchall()]

    all_unused_indexes = []

    # Step 2: Loop through each database
    for db in db_list:
        cursor.execute(f"USE [{db}];")
        cursor.execute("""
            WITH IndexStats AS
            (
                SELECT 
                    DB_NAME() AS DatabaseName,
                    OBJECT_SCHEMA_NAME(i.object_id) AS SchemaName,
                    OBJECT_NAME(i.object_id) AS TableName,
                    i.name AS IndexName,
                    i.index_id,
                    s.user_seeks, 
                    s.user_scans, 
                    s.user_lookups, 
                    s.user_updates,
                    i.type_desc AS IndexType,
                    SUM(ps.used_page_count) * 8 AS IndexSizeKB,
                    s.last_user_seek,
                    s.last_user_scan,
                    s.last_user_lookup,
                    s.last_user_update
                FROM sys.indexes AS i
                INNER JOIN sys.dm_db_index_usage_stats AS s
                    ON i.object_id = s.object_id 
                    AND i.index_id = s.index_id
                    AND s.database_id = DB_ID()
                INNER JOIN sys.dm_db_partition_stats AS ps
                    ON i.object_id = ps.object_id 
                    AND i.index_id = ps.index_id
                WHERE 
                    i.is_primary_key = 0 
                    AND i.is_unique_constraint = 0
                    AND i.name IS NOT NULL
                    AND i.type_desc = 'NONCLUSTERED'
                GROUP BY 
                    i.object_id, i.name, i.index_id, 
                    s.user_seeks, s.user_scans, s.user_lookups, s.user_updates, 
                    i.type_desc, s.last_user_seek, s.last_user_scan, s.last_user_lookup,
                    s.last_user_update
            )
            SELECT *,
                CASE 
                        WHEN (user_seeks + user_scans + user_lookups) = 0 
                            AND user_updates > 0 
                            THEN 'DROP'
                        WHEN (user_seeks + user_scans + user_lookups) < 100 
                            AND user_updates > 0
                            THEN 'LOW_READ'
                        ELSE 'KEEP'
                END AS Recommendation,
                'DROP INDEX [' + IndexName + '] ON [' + SchemaName + '].[' + TableName + '];' AS SuggestedIndexRemoveSQL
            FROM IndexStats
            ORDER BY Recommendation, IndexSizeKB DESC;
        """)
        for row in cursor.fetchall():
            all_unused_indexes.append({
                "database": row.DatabaseName,
                "schema": SchemaName.SchemaName,
                "table": row.TableName,
                "indexname": row.IndexName,
                "indexsizekb": row.IndexSizeKB,
                "recommendation": row.Recommendation,
                "suggestedindexremovesql": row.SuggestedIndexRemoveSQL
            })

    return all_unused_indexes


def get_missing_indexes_all_databases(connection):
    cursor = connection.cursor()

    # Step 1: Get all user databases
    cursor.execute("""
        SELECT name
        FROM sys.databases
        WHERE name NOT IN ('master','model','msdb','tempdb')
    """)
    db_list = [row.name for row in cursor.fetchall()]

    all_missing_indexes = []

    # Step 2: Loop through each database
    for db in db_list:
        cursor.execute(f"USE [{db}];")
        cursor.execute("""
            SELECT  
                DB_NAME() AS DatabaseName,
                OBJECT_SCHEMA_NAME(mid.object_id) AS SchemaName,
                OBJECT_NAME(mid.object_id) AS TableName,
                migs.user_seeks AS TimesNeeded,
                migs.avg_total_user_cost AS AvgCostImpact,
                migs.avg_user_impact AS AvgQueryImprovementPercent,
                CAST((migs.user_seeks * migs.avg_total_user_cost * 8) AS BIGINT) AS EstimatedSizeKB, -- rough estimate
                CASE 
                    WHEN migs.user_seeks > 50 AND migs.avg_user_impact > 70 
                    THEN 'YES' ELSE 'OPTIONAL' 
                END AS RecommendedToCreate,
                'CREATE NONCLUSTERED INDEX [IX_' + OBJECT_NAME(mid.object_id) + '_' +
                    REPLACE(REPLACE(ISNULL(mid.equality_columns,''),'[',''),']','') +
                    CASE 
                        WHEN mid.inequality_columns IS NOT NULL 
                        THEN '_' + REPLACE(REPLACE(mid.inequality_columns,'[',''),']','') 
                        ELSE '' 
                    END + '] ON ' + 
                    mid.statement + 
                    ' (' + ISNULL(mid.equality_columns,'') + 
                    CASE 
                        WHEN mid.inequality_columns IS NOT NULL 
                        THEN ',' + mid.inequality_columns 
                        ELSE '' 
                    END + ')' +
                    ISNULL(' INCLUDE (' + mid.included_columns + ')', '') AS SuggestedIndexSQL
            FROM sys.dm_db_missing_index_group_stats AS migs
            INNER JOIN sys.dm_db_missing_index_groups AS mig
                ON migs.group_handle = mig.index_group_handle
            INNER JOIN sys.dm_db_missing_index_details AS mid
                ON mig.index_handle = mid.index_handle
            WHERE OBJECT_SCHEMA_NAME(mid.object_id) IS NOT NULL 
            AND OBJECT_NAME(mid.object_id) IS NOT NULL
            ORDER BY 
                RecommendedToCreate DESC,
                migs.user_seeks DESC, 
                migs.avg_user_impact DESC;
        """)
        for row in cursor.fetchall():
            print(row)
            all_missing_indexes.append({
                "database": row.DatabaseName,
                "schema": row.SchemaName,
                "table": row.TableName,
                "timeneeded": row.TimesNeeded,
                "avgcostimpact": row.AvgCostImpact,
                "avgqueryimprovementpercent": row.AvgQueryImprovementPercent,
                "estimatedsizekb": row.EstimatedSizeKB,
                "recommendedtocreate": row.RecommendedToCreate,
                "suggestedindexsql": row.SuggestedIndexSQL
            })

    return all_missing_indexes

