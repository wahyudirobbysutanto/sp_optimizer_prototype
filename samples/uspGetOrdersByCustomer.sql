CREATE PROCEDURE uspGetOrdersByCustomer
    @CustomerID INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        soh.SalesOrderID,
        soh.OrderDate,
        soh.TotalDue,
        cust.AccountNumber,
        p.FirstName + ' ' + p.LastName AS CustomerName
    FROM Sales.SalesOrderHeader soh
    INNER JOIN Sales.Customer cust ON soh.CustomerID = cust.CustomerID
    INNER JOIN Person.Person p ON cust.PersonID = p.BusinessEntityID
    WHERE soh.CustomerID = @CustomerID;
END;
