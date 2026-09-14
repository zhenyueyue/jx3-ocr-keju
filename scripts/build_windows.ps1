$ErrorActionPreference = "Stop"

Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    uv sync --extra dev
    uv run pytest
    uv run pyinstaller --noconfirm --clean ocr-keju.spec
    Write-Host "Build complete: dist\ocr-keju\ocr-keju.exe"
}
finally {
    Pop-Location
}
