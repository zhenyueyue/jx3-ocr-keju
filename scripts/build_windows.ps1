$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot

function Get-PersistentDataDir {
    if (-not [string]::IsNullOrWhiteSpace($env:OCR_KEJU_DATA_DIR)) {
        return [System.IO.Path]::GetFullPath($env:OCR_KEJU_DATA_DIR)
    }
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        return Join-Path $env:LOCALAPPDATA "jx3-ocr-keju"
    }
    return Join-Path $env:USERPROFILE "AppData\Local\jx3-ocr-keju"
}

function Copy-NewerRuntimeData {
    param(
        [Parameter(Mandatory = $true)][string]$SourceDir,
        [Parameter(Mandatory = $true)][string]$DestinationDir
    )

    if (-not (Test-Path $SourceDir)) {
        return
    }

    $sourceFull = [System.IO.Path]::GetFullPath($SourceDir)
    $destinationFull = [System.IO.Path]::GetFullPath($DestinationDir)
    if ($sourceFull.TrimEnd('\') -eq $destinationFull.TrimEnd('\')) {
        return
    }

    Get-ChildItem -Path $sourceFull -File -Recurse | ForEach-Object {
        $relative = $_.FullName.Substring($sourceFull.TrimEnd('\').Length).TrimStart('\')
        $target = Join-Path $destinationFull $relative
        $targetParent = Split-Path -Parent $target
        New-Item -ItemType Directory -Path $targetParent -Force | Out-Null

        if (-not (Test-Path $target)) {
            Copy-Item $_.FullName $target -Force
            Write-Host "Migrated runtime data: $relative"
        }
    }
}

Push-Location $projectRoot
try {
    $persistentData = Get-PersistentDataDir
    New-Item -ItemType Directory -Path $persistentData -Force | Out-Null

    # Preserve existing local/user-added questions before PyInstaller replaces dist.
    Copy-NewerRuntimeData -SourceDir (Join-Path $projectRoot "data") -DestinationDir $persistentData
    Copy-NewerRuntimeData -SourceDir (Join-Path $projectRoot "dist\ocr-keju\data") -DestinationDir $persistentData

    uv sync --extra dev
    uv run pytest
    uv run pyinstaller --noconfirm --clean ocr-keju.spec
    Write-Host "Build complete: dist\ocr-keju\ocr-keju.exe"
    Write-Host "Persistent runtime data: $persistentData"
}
finally {
    Pop-Location
}
