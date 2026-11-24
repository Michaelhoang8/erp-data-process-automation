// Excel > Data > Get Data > From Other Sources > Blank Query.
// Create text parameter ReportFolder pointing to the successful reports/runs/<run_id> directory.
// Name this function LoadReport; then create individual queries as described in README.md.
(ReportName as text) as table =>
let
    Source = Csv.Document(File.Contents(ReportFolder & "/" & ReportName & ".csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Integers = {"AmountCents","PaidCents","OpenCents","DaysOverdue","InvoiceCount","Orders","ReceivedOrders","OnTimeOrders","OpenOverdueOrders","ReorderPoint","UnitCostCents","OnHand","ValueCents","InvoicedCents","Line"},
    Dates = {"PostingDate","DueDate"},
    Types = List.Transform(Table.ColumnNames(Headers), each {_, if List.Contains(Integers,_) then Int64.Type else if List.Contains(Dates,_) then type date else type text}),
    Typed = Table.TransformColumnTypes(Headers, Types, "en-CA"),
    CurrencyColumns = List.Select(Table.ColumnNames(Typed), each Text.EndsWith(_,"Cents")),
    Dollars = List.Accumulate(CurrencyColumns, Typed, (State,Column) => Table.AddColumn(State, Text.Replace(Column,"Cents","CAD"), each Record.Field(_,Column)/100, Currency.Type))
in
    Dollars
