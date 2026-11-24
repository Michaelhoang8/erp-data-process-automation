-- SQLite 3 dialect. Dates are ISO 8601; amounts are integer CAD cents.
-- Parameters contains the fixed reporting cutoff. Payments after cutoff excluded.
CREATE VIEW APDetail AS
WITH paid AS (
 SELECT InvoiceID,SUM(AmountCents) PaidCents FROM Payments
 WHERE PaymentDate <= (SELECT AsOf FROM Parameters) GROUP BY InvoiceID),
balances AS (
 SELECT i.*,v.VendorName,COALESCE(p.PaidCents,0) PaidCents,
 i.AmountCents-COALESCE(p.PaidCents,0) OpenCents,
 MAX(0,CAST(julianday((SELECT AsOf FROM Parameters))-julianday(i.DueDate) AS INTEGER)) DaysOverdue
 FROM Invoices i JOIN Vendors v USING(VendorID) LEFT JOIN paid p USING(InvoiceID)
 WHERE i.PostingDate <= (SELECT AsOf FROM Parameters))
SELECT *,CASE WHEN OpenCents<0 THEN 'Credit / overpayment'
 WHEN OpenCents=0 THEN 'Settled' WHEN DaysOverdue=0 THEN 'Current'
 WHEN DaysOverdue<=30 THEN '1-30 days' WHEN DaysOverdue<=60 THEN '31-60 days'
 WHEN DaysOverdue<=90 THEN '61-90 days' ELSE '90+ days' END AgingBucket
FROM balances;

CREATE VIEW APAging AS
SELECT AgingBucket,COUNT(*) InvoiceCount,SUM(OpenCents) OpenCents
FROM APDetail GROUP BY AgingBucket;

CREATE VIEW VendorPerformance AS
SELECT v.VendorID,v.VendorName,COUNT(*) Orders,
 SUM(CASE WHEN o.ReceivedDate IS NOT NULL AND o.ReceivedDate<=(SELECT AsOf FROM Parameters) THEN 1 ELSE 0 END) ReceivedOrders,
 SUM(CASE WHEN o.ReceivedDate IS NOT NULL AND o.ReceivedDate<=(SELECT AsOf FROM Parameters) AND o.ReceivedDate<=o.PromisedDate THEN 1 ELSE 0 END) OnTimeOrders,
 SUM(CASE WHEN (o.ReceivedDate IS NULL OR o.ReceivedDate>(SELECT AsOf FROM Parameters)) AND o.PromisedDate<(SELECT AsOf FROM Parameters) THEN 1 ELSE 0 END) OpenOverdueOrders
FROM PurchaseOrders o JOIN Vendors v USING(VendorID)
WHERE o.OrderDate<=(SELECT AsOf FROM Parameters) GROUP BY v.VendorID,v.VendorName;

CREATE VIEW InventoryPosition AS
SELECT m.ItemID,i.Description,m.Location,i.ReorderPoint,i.UnitCostCents,
 SUM(m.Quantity) OnHand,SUM(m.Quantity)*i.UnitCostCents ValueCents,
 CASE WHEN SUM(m.Quantity)<0 THEN 'Negative stock'
 WHEN SUM(m.Quantity)<i.ReorderPoint THEN 'Below reorder point' ELSE 'Within policy' END Status
FROM InventoryMovements m JOIN Items i USING(ItemID)
WHERE m.PostingDate<=(SELECT AsOf FROM Parameters)
GROUP BY m.ItemID,i.Description,m.Location,i.ReorderPoint,i.UnitCostCents;

CREATE VIEW MonthlyInvoiceTrend AS
SELECT substr(PostingDate,1,7) Month,COUNT(*) InvoiceCount,SUM(AmountCents) InvoicedCents
FROM Invoices WHERE PostingDate<=(SELECT AsOf FROM Parameters) GROUP BY substr(PostingDate,1,7);
