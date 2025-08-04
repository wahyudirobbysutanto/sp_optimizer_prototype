
USE master
GO
------------------------------------------------------------
-- 1. Create Databases
------------------------------------------------------------
IF DB_ID('SalesDB') IS NOT NULL DROP DATABASE SalesDB;
IF DB_ID('InventoryDB') IS NOT NULL DROP DATABASE InventoryDB;
GO

CREATE DATABASE SalesDB;
GO
CREATE DATABASE InventoryDB;
GO

------------------------------------------------------------
-- 2. Create Tables
------------------------------------------------------------

-- SalesDB tables
USE SalesDB;
DROP TABLE IF EXISTS Customers
DROP TABLE IF EXISTS Orders
GO

CREATE TABLE Customers (
    CustomerID INT PRIMARY KEY,
    CustomerName NVARCHAR(100)
);

CREATE TABLE Orders (
    OrderID INT PRIMARY KEY,
    CustomerID INT,
    ProductID INT,
    Quantity INT,
    OrderDate DATE
);

-- InventoryDB table
USE InventoryDB;
DROP TABLE IF EXISTS Products
GO

CREATE TABLE Products (
    ProductID INT PRIMARY KEY,
    ProductName NVARCHAR(100),
    Stock INT
);

------------------------------------------------------------
-- 3. Insert Sample Data
------------------------------------------------------------

-- Base data
USE SalesDB;
GO
INSERT INTO Customers VALUES (1, 'Alice'), (2, 'Bob');

INSERT INTO Orders VALUES 
(101, 1, 1001, 2, '2024-01-01'),
(102, 2, 1002, 1, '2024-01-02');

USE InventoryDB;
GO
INSERT INTO Products VALUES
(1001, 'Keyboard', 50),
(1002, 'Mouse', 150);

-- Add more rows for performance testing
USE SalesDB;
GO
-- Add 10k customers
INSERT INTO Customers (CustomerID, CustomerName)
SELECT TOP 10000 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) + 2,
       'Customer_' + CAST(ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS NVARCHAR(10))
FROM sys.all_objects;

-- Add 50k orders
INSERT INTO Orders (OrderID, CustomerID, ProductID, Quantity, OrderDate)
SELECT TOP 50000
    ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) + 102,
    ABS(CHECKSUM(NEWID())) % 10000 + 1, 
    CASE WHEN ABS(CHECKSUM(NEWID())) % 2 = 0 THEN 1001 ELSE 1002 END,
    ABS(CHECKSUM(NEWID())) % 5 + 1,
    DATEADD(DAY, -ABS(CHECKSUM(NEWID())) % 365, GETDATE())
FROM sys.all_objects a
CROSS JOIN sys.all_objects b;

------------------------------------------------------------
-- 4. Create Stored Procedures
------------------------------------------------------------

USE SalesDB;
DROP PROCEDURE IF EXISTS usp_SlowOrderReport
GO


-- Slow SP: scans all data, cross-database join, no filtering
CREATE PROCEDURE usp_SlowOrderReport
AS
BEGIN
    SELECT *
    FROM Customers c
    JOIN Orders o ON c.CustomerID = o.CustomerID
    JOIN InventoryDB.dbo.Products p ON p.ProductID = o.ProductID
    ORDER BY c.CustomerName;
END;
GO

USE master
GO



/*
-- Index to support optimized SP
CREATE NONCLUSTERED INDEX IX_Orders_CustomerID 
ON Orders(CustomerID) INCLUDE (ProductID, Quantity, OrderDate);

-- Fast SP: filters data, selects columns explicitly
CREATE PROCEDURE usp_FastOrderReport
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        c.CustomerName,
        o.OrderID,
        o.ProductID,
        o.Quantity,
        o.OrderDate,
        p.ProductName,
        p.Stock
    FROM Orders o
    INNER JOIN Customers c ON o.CustomerID = c.CustomerID
    INNER JOIN InventoryDB.dbo.Products p ON o.ProductID = p.ProductID
    WHERE o.OrderDate >= DATEADD(DAY, -30, GETDATE())
    ORDER BY o.OrderDate DESC;
END;
GO

*/
------------------------------------------------------------
-- 5. How to Test
------------------------------------------------------------
-- EXEC SalesDB.dbo.usp_SlowOrderReport;
-- EXEC SalesDB.dbo.usp_FastOrderReport;
------------------------------------------------------------
PRINT 'Multi-database demo setup completed successfully.';
