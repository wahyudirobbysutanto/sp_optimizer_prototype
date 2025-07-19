CREATE PROCEDURE uspFindCustomersByRegion
    @Region NVARCHAR(50),
    @City NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        l.CustomerID,
        l.SearchDate,
        l.SearchKeyword,
        c.AccountNumber
    FROM dbo.CustomerSearchLog l
    INNER JOIN Sales.Customer c ON l.CustomerID = c.CustomerID
    WHERE l.Region = @Region AND l.City = @City
    ORDER BY l.SearchDate DESC;
END
