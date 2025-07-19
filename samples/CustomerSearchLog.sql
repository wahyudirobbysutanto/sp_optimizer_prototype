CREATE TABLE dbo.CustomerSearchLog (
    LogID INT IDENTITY(1,1) PRIMARY KEY,
    CustomerID INT NOT NULL,
    SearchDate DATETIME NOT NULL DEFAULT GETDATE(),
    Region NVARCHAR(50),
    City NVARCHAR(50),
    SearchKeyword NVARCHAR(100)
);
