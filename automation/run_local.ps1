param([string]$AsOf = '2025-12-31', [string]$PythonExe = 'python')
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
& $PythonExe (Join-Path $ProjectRoot 'src/run_pipeline.py') --as-of $AsOf
if ($LASTEXITCODE -ne 0) { throw "ERP reporting pipeline failed with exit code $LASTEXITCODE" }
# Local execution only. Does not create a schedule, send a message, or change ERP data.
