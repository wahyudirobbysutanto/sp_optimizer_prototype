USE master
GO

DROP DATABASE IF EXISTS TestDB
GO

CREATE DATABASE TestDB;
GO


IF NOT EXISTS (
    SELECT 1 FROM sys.indexes 
    WHERE name = 'IX_DemoFragment' 
      AND object_id = OBJECT_ID('Sales.SalesOrderDetail')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_DemoFragment
    ON AdventureWorks2019.Sales.SalesOrderDetail (ProductID);
END
GO


IF OBJECT_ID('dbo.DemoOrders') IS NULL
BEGIN
    CREATE TABLE TestDB.dbo.DemoOrders (
        OrderID INT IDENTITY PRIMARY KEY,
        ProductID INT,
        Qty INT
    );

    -- Fill with some dummy data
    INSERT INTO TestDB.dbo.DemoOrders (ProductID, Qty)
    SELECT TOP 5000 ABS(CHECKSUM(NEWID())) % 100, 1
    FROM sys.objects a CROSS JOIN sys.objects b;
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes 
    WHERE name = 'IX_DemoFragment' 
      AND object_id = OBJECT_ID('dbo.DemoOrders')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_DemoFragment
    ON TestDB.dbo.DemoOrders (ProductID);
END
GO

-- for fragmentation

DECLARE @i INT = 0;
WHILE @i < 100
BEGIN
    UPDATE TOP (1000) AdventureWorks2019.Sales.SalesOrderDetail
    SET ProductID = ProductID;
    
    SET @i += 1;
END;
GO

DECLARE @i INT = 0;
WHILE @i < 100
BEGIN
    UPDATE TOP (1000) TestDB.dbo.DemoOrders
    SET ProductID = ProductID;
    
    SET @i += 1;
END;

--

USE master
GO
