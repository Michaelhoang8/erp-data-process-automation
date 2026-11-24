DROP VIEW IF EXISTS AnnualReview;
CREATE VIEW AnnualReview AS SELECT Year,COUNT(*) SourceRows,
 SUM(AmountCents) NetCents,SUM(CASE WHEN AmountCents>0 THEN AmountCents ELSE 0 END) PositiveCents,
 SUM(CASE WHEN AmountCents<0 THEN AmountCents ELSE 0 END) NegativeCents,
 SUM(CASE WHEN Contract='DV' AND AmountCents>0 THEN AmountCents ELSE 0 END) DirectVoucherPositiveCents,
 SUM(CASE WHEN Precision='Annual rollup' THEN 1 ELSE 0 END) RollupRows,
 COUNT(DISTINCT Vendor) Vendors FROM Payments GROUP BY Year;
DROP VIEW IF EXISTS MonthlyReview;
CREATE VIEW MonthlyReview AS SELECT SUBSTR(Date,1,7) Month,Year,COUNT(*) SourceRows,SUM(AmountCents) NetCents
 FROM Payments WHERE Precision='Dated record' GROUP BY SUBSTR(Date,1,7),Year;
DROP VIEW IF EXISTS VendorReview;
CREATE VIEW VendorReview AS SELECT Year,Vendor,COUNT(*) SourceRows,SUM(AmountCents) NetCents,
 SUM(CASE WHEN AmountCents>0 THEN AmountCents ELSE 0 END) PositiveCents
 FROM Payments GROUP BY Year,Vendor;
DROP VIEW IF EXISTS DepartmentReview;
CREATE VIEW DepartmentReview AS SELECT Year,Department,COUNT(*) SourceRows,SUM(AmountCents) NetCents
 FROM Payments GROUP BY Year,Department;
