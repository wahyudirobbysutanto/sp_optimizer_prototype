
USE master
GO

------------------------------------------------------------
-- 1. Create FinanceDB
------------------------------------------------------------
IF DB_ID('FinanceDB') IS NOT NULL DROP DATABASE FinanceDB;
GO
CREATE DATABASE FinanceDB;
GO

------------------------------------------------------------
-- 2. Create Extra Tables
------------------------------------------------------------

USE FinanceDB;
DROP TABLE IF EXISTS Payments
DROP TABLE IF EXISTS TaxRates
GO


-- Payments table
CREATE TABLE Payments (
    PaymentID INT PRIMARY KEY,
    OrderID INT,
    PaymentDate DATE,
    Amount DECIMAL(18,2)
);

-- TaxRates table
CREATE TABLE TaxRates (
    Region NVARCHAR(50),
    TaxRate DECIMAL(5,2)
);

------------------------------------------------------------
-- 3. Insert Data
------------------------------------------------------------

-- Fill Payments (link to Orders from SalesDB)
INSERT INTO Payments (PaymentID, OrderID, PaymentDate, Amount)
SELECT TOP 40000
    ROW_NUMBER() OVER (ORDER BY (SELECT NULL)),
    100 + ROW_NUMBER() OVER (ORDER BY (SELECT NULL)),
    DATEADD(DAY, -ABS(CHECKSUM(NEWID())) % 365, GETDATE()),
    (ABS(CHECKSUM(NEWID())) % 500) + 100
FROM sys.all_objects a
CROSS JOIN sys.all_objects b;

-- TaxRates: only a few rows
INSERT INTO TaxRates VALUES
('North', 10.0),
('South', 8.0),
('East', 7.5),
('West', 12.0);

------------------------------------------------------------
-- 4. Create a Heavy Stored Procedure
------------------------------------------------------------

USE SalesDB;
DROP PROCEDURE IF EXISTS usp_HeavyCrossDBReport
GO

CREATE PROCEDURE usp_HeavyCrossDBReport
AS
BEGIN
    -- Intentionally BAD:
    -- * Select *
    -- * No filters
    -- * Join across 3 DBs
    -- * Extra sort and aggregation
    SELECT *
    FROM Customers c
    JOIN Orders o ON c.CustomerID = o.CustomerID
    JOIN InventoryDB.dbo.Products p ON o.ProductID = p.ProductID
    JOIN FinanceDB.dbo.Payments pay ON pay.OrderID = o.OrderID
    LEFT JOIN FinanceDB.dbo.TaxRates tr ON tr.Region = 
        CASE 
            WHEN c.CustomerID % 4 = 0 THEN 'North'
            WHEN c.CustomerID % 4 = 1 THEN 'South'
            WHEN c.CustomerID % 4 = 2 THEN 'East'
            ELSE 'West'
        END
    ORDER BY c.CustomerName, pay.PaymentDate;

    -- Force extra work with a useless aggregate
    -- (You can remove this part if you want even worse performance)
    SELECT c.CustomerName, SUM(pay.Amount)
    FROM Customers c
    JOIN Orders o ON c.CustomerID = o.CustomerID
    JOIN FinanceDB.dbo.Payments pay ON pay.OrderID = o.OrderID
    GROUP BY c.CustomerName
    ORDER BY SUM(pay.Amount) DESC;
END;
GO

USE master
GO
