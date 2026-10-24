# Cai dat Medical Chatbot tren may Windows.
# Nhap dup file scripts\cai_dat_app.bat de chay (hoac:
#   powershell -ExecutionPolicy Bypass -File scripts\cai_dat_app.ps1)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== Cai dat Medical Chatbot ==="
Write-Host "Thu muc du an: $root"
Write-Host ""

# ---------- 1. Kiem tra dia trong (venv + torch nang khoang 5-6 GB) ----------
$drive = Get-PSDrive -Name $root.Substring(0, 1)
$freeGB = [math]::Round($drive.Free / 1GB)
if ($freeGB -lt 6) {
    Write-Host "CANH BAO: dia $($root.Substring(0,1)): chi con $freeGB GB trong. Cai dat can khoang 6 GB."
    $ans = Read-Host "Van tiep tuc? (y/n)"
    if ($ans -notmatch '^(y|Y|c|C)$') { exit 1 }
}

# ---------- 2. Kiem tra Python >= 3.10 ----------
function Get-Python {
    $cands = @()
    if (Get-Command py -ErrorAction SilentlyContinue) { $cands += "py" }
    foreach ($p in @(
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
    )) {
        if (Test-Path $p) { $cands += $p }
    }
    $pp = Get-Command python -ErrorAction SilentlyContinue
    if ($pp -and $pp.Source -notlike "*WindowsApps*") { $cands += "python" }
    foreach ($c in $cands) {
        $v = "$(& $c -V 2>&1)"
        if ($v -match "Python (\d+)\.(\d+)") {
            if ([int]$Matches[1] -gt 3 -or ([int]$Matches[1] -eq 3 -and [int]$Matches[2] -ge 10)) {
                return $c
            }
        }
    }
    return $null
}

$py = Get-Python
if (-not $py) {
    Write-Host ""
    Write-Host "May chua co Python 3.10 hoac moi hon."
    Write-Host "Trang tai: https://www.python.org/downloads/"
    Write-Host "(Khi cai, nho tick 'Add python.exe to PATH')"
    $ans = Read-Host "Ban co muon toi cai Python qua winget? (y/n)"
    if ($ans -match '^(y|Y|c|C)$') {
        try {
            & winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
        } catch {
            Write-Host "winget loi hoac khong co: $($_.Exception.Message)"
        }
        $env:Path = "$env:LOCALAPPDATA\Programs\Python\Python312\Scripts;$env:LOCALAPPDATA\Programs\Python\Python312;" + $env:Path
        $py = Get-Python
    }
    if (-not $py) {
        Write-Host "Khong tim thay Python. Hay cai theo link tren (tick Add to PATH),"
        Write-Host "roi dong cua so nay va chay lai cai_dat_app.bat."
        exit 1
    }
}
Write-Host "Python: $(& $py -V)"

# ---------- 3. Tao moi truong ao + cai thu vien ----------
$venvPy = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host ""
    Write-Host "Tao moi truong ao .venv ..."
    & $py -m venv .venv
}
if (-not (Test-Path $venvPy)) {
    Write-Host "Khong tao duoc .venv. Hay chay lai script."
    exit 1
}
Write-Host ""
Write-Host "Cai thu vien (torch nang, lan dau co the doi 5-15 phut) ..."
& $venvPy -m pip install --upgrade pip --quiet
& $venvPy -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Cai thu vien that bai. Kiem tra mang roi chay lai script."
    exit 1
}
Write-Host "Da cai xong thu vien."

# ---------- 4. Giai nen model NER ----------
if (-not (Test-Path "models\ner_model\config.json")) {
    if (Test-Path "models\ner_model.zip") {
        Write-Host ""
        Write-Host "Giai nen models\ner_model.zip (786 MB, doi mot luat) ..."
        $tmp = Join-Path $env:TEMP ("ner_extract_" + [guid]::NewGuid().ToString("N"))
        Expand-Archive -Path "models\ner_model.zip" -DestinationPath $tmp -Force
        $cfg = Get-ChildItem $tmp -Recurse -Filter config.json | Select-Object -First 1
        if ($cfg) {
            $srcDir = Split-Path -Parent $cfg.FullName
            New-Item -ItemType Directory -Path "models\ner_model" -Force | Out-Null
            Move-Item -Path (Join-Path $srcDir "*") -Destination "models\ner_model" -Force
            Write-Host "Da giai nen xong models\ner_model."
        } else {
            Write-Host "CANH BAO: nen khong thay config.json trong ner_model.zip."
        }
        Remove-Item $tmp -Recurse -Force
    } else {
        Write-Host ""
        Write-Host "CANH BAO: thieu models\ner_model.zip - phan NER se khong chay duoc."
    }
} else {
    Write-Host ""
    Write-Host "Model NER da co san (models\ner_model)."
}

# ---------- 5. Kiem tra vector database ----------
if (-not (Test-Path "app\db\chroma_db")) {
    Write-Host ""
    Write-Host "CANH BAO: thieu app\db\chroma_db (vector database)."
    Write-Host "Can build lai bang cac lenh (tu thu muc du an):"
    Write-Host "  .venv\Scripts\python.exe app\services\ingest.py"
    Write-Host "  .venv\Scripts\python.exe app\services\ingest_kb.py"
    Write-Host "  .venv\Scripts\python.exe app\services\ingest_vimedaqa.py"
} else {
    Write-Host "Vector database da co san (app\db\chroma_db) - khong can ingest lai."
}

# ---------- 6. Chon + tai model Ollama (chay trong cua so rieng) ----------
Write-Host ""
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "chon_model.ps1")

Write-Host ""
Write-Host "=== HOAN TAT ==="
Write-Host "Nhap dup file scripts\chay_app.bat de mo chatbot."
