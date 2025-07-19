-- Create index on Sales.SalesOrderDetail table if it does not exist
use AdventureWorks2019;
GO

IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_DemoFragment' AND object_id = OBJECT_ID('Sales.SalesOrderDetail')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_DemoFragment
    ON Sales.SalesOrderDetail (ProductID);
END;

-- loop to update rows in Sales.SalesOrderDetail table
-- This will create fragmentation in the index
SET NOCOUNT ON;
GO

DECLARE @i INT = 0;
WHILE @i < 100
BEGIN
    UPDATE TOP (1000) Sales.SalesOrderDetail
    SET ProductID = ProductID;
    
    SET @i += 1;
END;
