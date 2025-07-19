CREATE PROCEDURE uspGetProductSalesInfo
    @ProductID INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        sod.*,
        p.Name AS a,
        p.ProductNumber
    FROM Sales.SalesOrderDetail sod
    INNER JOIN Production.Product p ON sod.ProductID = p.ProductID
    WHERE sod.ProductID = @ProductID;
END
