// Paste into a blank query; set ReportFolder to the local reports directory.
let
 ReportFolder = "C:\path\to\erp-data-process-automation\reports",
 Source = Csv.Document(File.Contents(ReportFolder & "\annual_summary.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
 Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
 Typed = Table.TransformColumnTypes(Headers, {{"Year", Int64.Type}, {"SourceRows", Int64.Type}, {"NetCents", Int64.Type}, {"PositiveCents", Int64.Type}, {"NegativeCents", Int64.Type}, {"DirectVoucherPositiveCents", Int64.Type}, {"RollupRows", Int64.Type}, {"Vendors", Int64.Type}}),
 NetUSD = Table.AddColumn(Typed, "NetUSD", each [NetCents] / 100, Currency.Type)
in NetUSD
