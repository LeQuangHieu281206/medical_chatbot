# Chon model Ollama phu hop voi may Windows.
# Chay: powershell -ExecutionPolicy Bypass -File scripts\chon_model.ps1
# Them -Pull de lay luon model duoc goi y (khong hoi): ... chon_model.ps1 -Pull
param([switch]$Pull)

$ErrorActionPreference = "SilentlyContinue"
$root = Split-Path -Parent $PSScriptRoot

# ---------- 1. Doc cau hinh may ----------
$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
$cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name

$vramGB = 0.0
$gpuName = "khong ro"

if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $line = & nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits |
        Select-Object -First 1
    if ($line) {
        $gpuName, $vramMB = $line -split ',\s*'
        $vramGB = [math]::Round([double]$vramMB / 1024, 1)
    }
}

# AMD/Intel: AdapterRAM cua WMI bi tran 32-bit, nen doc qwMemorySize tu registry.
if ($vramGB -eq 0) {
    $keys = Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0*"
    $best = $keys | Where-Object { $_.'HardwareInformation.qwMemorySize' } |
        Sort-Object { [int64]$_.'HardwareInformation.qwMemorySize' } | Select-Object -Last 1
    if ($best) {
        $vramGB = [math]::Round([int64]$best.'HardwareInformation.qwMemorySize' / 1GB, 1)
        $gpuName = $best.DriverDesc
    } else {
        $gpuName = (Get-CimInstance Win32_VideoController | Select-Object -First 1).Name
    }
}

$freeGB = [math]::Round((Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace / 1GB)

Write-Host ""
Write-Host "=== May cua ban ==="
Write-Host "CPU : $cpu"
Write-Host "RAM : $ramGB GB"
Write-Host "GPU : $gpuName"
Write-Host "VRAM: $vramGB GB"
Write-Host "Trong o C: $freeGB GB"

# ---------- 2. Catalog model (moi tag deu co tren ollama.com) ----------
# size = dung luong tai ve (GB). Model sap xep theo dung luong tang dan.
$models = @(
    @{ tag = "qwen3.5:4b";       size = 3.3;  note = "mac dinh, tieng Viet tot, nhanh" },
    @{ tag = "medgemma:4b";      size = 3.3;  note = "chuyen y te (tu Gemma 3)" },
    @{ tag = "gemma3:4b";        size = 3.4;  note = "da ngon ngu tot (140+ ngon ngu)" },
    @{ tag = "llama3.1:8b";      size = 4.9;  note = "tieng Viet trung binh" },
    @{ tag = "deepseek-r1:8b";   size = 4.9;  note = "suy luan manh, tra loi cham hon" },
    @{ tag = "aya-expanse:8b";   size = 5.1;  note = "chinh thuc ho tro tieng Viet (Cohere)" },
    @{ tag = "glm4:9b";          size = 5.5;  note = "da ngon ngu" },
    @{ tag = "qwen3.5:9b";       size = 6.6;  note = "can bang chat luong / toc do" },
    @{ tag = "mistral-nemo:12b"; size = 7.1;  note = "da ngon ngu, context 1M" },
    @{ tag = "gemma3:12b";       size = 8.2;  note = "chat luong cao hon" },
    @{ tag = "qwen3.5:27b";      size = 17.0; note = "chat luong cao" },
    @{ tag = "gemma3:27b";       size = 17.0; note = "chat luong cao" },
    @{ tag = "medgemma:27b";     size = 17.0; note = "chuyen y te, manh nhat ve y khoa" },
    @{ tag = "aya-expanse:32b";  size = 20.0; note = "tieng Viet chinh thuc, chat luong cao" },
    @{ tag = "qwen3.5:35b-a3b";  size = 22.0; note = "MoE, nhanh voi chat luong tot nhat" }
)

# ---------- 3. Bo loc theo VRAM / RAM ----------
if ($vramGB -ge 5) {
    $budget = $vramGB * 0.9      # du cho KV cache (ctx 4096) + man hinh
    $cpuMode = $false
} else {
    $budget = $ramGB * 0.4       # chi CPU: model + phu thuoc phai vua RAM
    $cpuMode = $true
    Write-Host ""
    Write-Host "LUU Y: Khong co GPU du manh. Model se chay tren CPU, rat cham (vai token/giay)."
}

$fits = @($models | Where-Object { $_.size -le $budget } | Sort-Object size)

if ($fits.Count -eq 0) {
    Write-Host ""
    Write-Host "May khong du RAM/VRAM cho model nao trong danh sach."
    Write-Host "Van co the thu qwen3.5:4b (3.3 GB), nhung se rat cham hoac loi het bo nho."
    $fits = @($models | Where-Object { $_.tag -eq "qwen3.5:4b" })
    $default = $fits[0]
} else {
    # Goi y mac dinh: qwen3.5 lon nhat vua may; neu khong co thi model lon nhat vua may
    $default = $fits | Where-Object { $_.tag -like "qwen3.5*" } | Select-Object -Last 1
    if (-not $default) { $default = $fits | Select-Object -Last 1 }
}

# ---------- 4. Hien thi danh sach de chon ----------
Write-Host ""
Write-Host "=== Model phu hop voi may ban ==="
$i = 1
foreach ($m in $fits) {
    $mark = ""
    if ($m.tag -eq $default.tag) { $mark = "  <-- goi y (Enter)" }
    Write-Host ("  [{0}] {1,-20} {2,5} GB  {3}{4}" -f $i, $m.tag, $m.size, $m.note, $mark)
    $i++
}
$skip = @($models | Where-Object { $_.size -gt $budget }).Count
if ($skip -gt 0) {
    Write-Host ("  (an di {0} model khong vua bo nho may)" -f $skip)
}

if ($Pull) {
    $tag = $default.tag
    Write-Host ""
    Write-Host "Chon (vi co -Pull): $tag"
} else {
    Write-Host ""
    $choice = Read-Host "Chon so [1-$($fits.Count)] (Enter = goi y)"
    $idx = 0
    if ([int]::TryParse($choice, [ref]$idx) -and $idx -ge 1 -and $idx -le $fits.Count) {
        $tag = $fits[$idx - 1].tag
    } else {
        $tag = $default.tag
    }
}
Write-Host ""
Write-Host "Da chon: $tag"

# ---------- 5. Kiem tra Ollama (thieu thi tu tai cai neu dong y) ----------
$ollamaExe = $null
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    $ollamaExe = "ollama"
} else {
    foreach ($p in @("$env:LOCALAPPDATA\Programs\Ollama\ollama.exe", "C:\Program Files\Ollama\ollama.exe")) {
        if (Test-Path $p) { $ollamaExe = $p; break }
    }
}

if (-not $ollamaExe) {
    Write-Host ""
    Write-Host "May chua cai Ollama."
    Write-Host "Trang tai: https://ollama.com/download/windows"
    $ans = Read-Host "Ban co muon toi tu tai va cai Ollama bay gio? (y/n)"
    if ($ans -match '^(y|Y|c|C)$') {
        $setup = "$env:TEMP\OllamaSetup.exe"
        Write-Host "Dang tai OllamaSetup.exe (khoang 700 MB) ..."
        $ProgressPreference = "SilentlyContinue"
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $setup -UseBasicParsing
        if (-not (Test-Path $setup)) {
            Write-Host "Tai that bai. Hay tai thu cong theo link tren, cai xong chay lai script."
            exit 1
        }
        Write-Host "Dang cai dat - neu hien cua so cai dat, hay nhan Install va doi xong."
        Start-Process -FilePath $setup -Wait
        foreach ($p in @("$env:LOCALAPPDATA\Programs\Ollama\ollama.exe", "C:\Program Files\Ollama\ollama.exe")) {
            if (Test-Path $p) { $ollamaExe = $p; break }
        }
        if ((-not $ollamaExe) -and (Get-Command ollama -ErrorAction SilentlyContinue)) { $ollamaExe = "ollama" }
        if (-not $ollamaExe) {
            Write-Host "Khong tim thay ollama.exe sau khi cai."
            Write-Host "Hay dong cua so nay, mo cua so PowerShell moi va chay lai script."
            exit 1
        }
        Write-Host "Da cai Ollama xong."
    } else {
        Write-Host "Khong co Ollama thi khong tai model duoc. Tai tai: https://ollama.com/download/windows"
        exit 1
    }
}

# ---------- 6. Kiem tra dung luong trong truoc khi tai ----------
$model = $models | Where-Object { $_.tag -eq $tag } | Select-Object -First 1
if ($model -and $freeGB -lt ($model.size * 1.2)) {
    Write-Host ""
    Write-Host "CANH BAO: O C chi con $freeGB GB, trong khi model can khoang $([math]::Round($model.size * 1.2, 1)) GB."
}

# ---------- 7. Tai model ----------
if (-not $Pull) {
    $ans = Read-Host "Tai model $tag ngay? (y/n)"
    if ($ans -notmatch '^(y|Y|c|C)$') {
        Write-Host "Da huy. Khi muon tai, chay lai script hoac dung lenh:"
        Write-Host "  ollama pull $tag"
        exit 0
    }
}
Write-Host ""
Write-Host "Dang tai $tag ... (doi vai phut tuy mang)"
& $ollamaExe pull $tag
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tai loi. Kiem tra mang roi chay lai script."
    exit 1
}
Write-Host "Da tai xong $tag."

# ---------- 8. Thu nhanh toc do ----------
Write-Host ""
Write-Host "Thu model voi 1 cau ngan (lan dau chay se cham hon)..."
$out = & $ollamaExe run $tag "Tra loi ngan gon: Vitamin C co tac dung gi?" --verbose 2>&1 | Out-String
$m = [regex]::Match($out, "eval rate:\s*([\d\.]+)")
if ($m.Success) {
    Write-Host ("Toc do khoang " + $m.Groups[1].Value + " token/giay")
} else {
    Write-Host "Khong do duoc toc do (khong sao, model van da tai thanh cong)."
}

# ---------- 9. Luu lua chon ----------
Set-Content -Path (Join-Path $root "ollama_model.txt") -Value $tag -Encoding ASCII
Write-Host ""
Write-Host "Da luu model chon vao ollama_model.txt (chay_app.bat se tu dung model nay)."

$ans = Read-Host "Dat $tag lam mac dinh vinh vien cho may (setx OLLAMA_MODEL)? (y/n)"
if ($ans -match '^(y|Y|c|C)$') {
    setx OLLAMA_MODEL $tag | Out-Null
    Write-Host "Da dat. Hieu luc cho moi cua so PowerShell (cua so hien tai khong doi)."
}

Write-Host ""
Write-Host "=== Xong! Cach chay chatbot ==="
Write-Host "Cach 1 (de nhat): nhap dup file scripts\chay_app.bat"
Write-Host "Cach 2 (PowerShell, tu thu muc du an):"
Write-Host ('  $env:OLLAMA_MODEL = "' + $tag + '"')
Write-Host "  streamlit run app\ui.py"
