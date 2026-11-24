# Excel operations review

Open **ERP_Operations_Review.xlsx** for a populated workbook with payable aging, formula-based balances and stock valuation, an editable review queue, named Excel tables and an aging chart. It is a snapshot of the generated synthetic reporting run; it does not contain a live Business Central connection.

The four PNGs in `docs/screenshots/excel-*.png` are workbook renders, not screenshots of Microsoft Excel. Formulas were recalculated and checked with the artifact workbook engine. Native Excel execution has not been tested.

`LoadReport.pq` is import-ready Power Query M: paste into a blank query in Excel or Power BI, set the report folder and filename, and refresh. The workbook's ActionQueue table can be selected by Excel Online (Business) after uploading the workbook to your own OneDrive or SharePoint. Configure connections and reviewers in your tenant; no cloud flow is installed.

Workbook authoring source: `scripts/build_workbook.mjs` and `scripts/prepare_workbook.py`. The builder requires the OpenAI artifact-tool runtime (used to generate this checked-in workbook); it is optional and not needed to run the Python/SQL project or open the XLSX. Run the preparation script after a pipeline refresh before rebuilding.
