Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -TypeDefinition @"
using System; using System.IO;
public static class Crc32 {
    static readonly uint[] T;
    static Crc32() {
        T = new uint[256];
        for (uint i = 0; i < 256; i++) {
            uint c = i;
            for (int j = 0; j < 8; j++) c = (c & 1) != 0 ? 0xEDB88320u ^ (c >> 1) : c >> 1;
            T[i] = c;
        }
    }
    public static uint Compute(string path) {
        uint c = 0xFFFFFFFF;
        using (var f = File.OpenRead(path)) {
            var b = new byte[65536]; int r;
            while ((r = f.Read(b, 0, b.Length)) > 0)
                for (int i = 0; i < r; i++) c = T[(c ^ b[i]) & 0xFF] ^ (c >> 8);
        }
        return c ^ 0xFFFFFFFF;
    }
}
"@ -ErrorAction SilentlyContinue

# =================================================
# PATH CONFIG
# =================================================
$VAM_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PREFS_FILE = "$VAM_DIR\prefs.json"
$LOG_DIR = "$VAM_DIR\logs"
$ROOT_DXGI = "$VAM_DIR\dxgi.dll"
$DXGI_DISABLED = "$VAM_DIR\dxgi.disabled"
$ISLC_EXE = "$VAM_DIR\software\Programs\ISLC v1.0.3.4\Intelligent standby list cleaner ISLC.exe"
$RAMDISK_EXE = "C:\Program Files\SoftPerfect RAM Disk\ramdisk.exe"
$ZAJE_SRC = "$VAM_DIR\for Ram Drive\zaje"
$ZAJE_DST = "Z:\Zaje"
$SESSION_LOG = "$LOG_DIR\sessions_steam.log"
$BG_FOLDER = "$VAM_DIR\background"
$BG_EXTRA = "$VAM_DIR\zajebanan"
$ROOT = $VAM_DIR.Substring(0,2)
$STEAM_URI = "steam://rungameid/17425422553224052736"
$MONO_DIR = "$VAM_DIR\Mono\EmbedRuntime"
$MONO_CURRENT = "$MONO_DIR\mono.dll"
$PATCH_STASH = "$VAM_DIR\software\PatchStash"
$MONO_DEFAULT     = "$PATCH_STASH\Mono\mono.default.dll"
$MONO_PATCHED     = "$PATCH_STASH\Mono\mono.patched.dll"
$MONO_ZIP         = "$VAM_DIR\software\Peformace Patches\3x Patch for MAX_HEAP_SECTS.zip"
$MONO_CRC_DEFAULT = 1622536192
$MONO_CRC_PATCHED = 466937454
$PERF_DIR = "$VAM_DIR\PerformancePatches"
$ASM_DIRS = @("$VAM_DIR\VaM_Data\Managed", "$VAM_DIR\sotr_Data\Managed")
$ASM_STASH = @("$PATCH_STASH\VaM_Data", "$PATCH_STASH\sotr_Data")
$FSR_STASH = "$PATCH_STASH\OpenVR_FSR"
$PLUGIN_DIRS = @("$VAM_DIR\VaM_Data\Plugins", "$VAM_DIR\sotr_Data\Plugins")
$PATCH_DIR        = "$VAM_DIR\software\VaM\Plugins\Patches"
$BEPINEX_ZIP_X64  = "$VAM_DIR\software\BepInEx\BepInEx_win_x64_5.4.23.2.zip"
$BEPINEX_ZIP_X86  = "$VAM_DIR\software\BepInEx\BepInEx_win_x86_5.4.23.2.zip"
$BEPINEX_DLL      = "$VAM_DIR\winhttp.dll"
$BEPINEX_DISABLED = "$VAM_DIR\winhttp.dll.disabled"
$BEPINEX_STASH    = "$PATCH_STASH\BepInEx"
$BEPINEX_CRC_X64    = 2163035466
$BEPINEX_CRC_X86    = 1497377181
$BEPINEX_ZIP_X64_21 = "$VAM_DIR\software\BepInEx\BepInEx_x64_5.4.21.0.zip"
$BEPINEX_ZIP_X86_21 = "$VAM_DIR\software\BepInEx\BepInEx_x86_5.4.21.0.zip"
$BEPINEX_CRC_X64_21 = 2878823013
$BEPINEX_CRC_X86_21 = 1929885738

$_v102zip = (Get-ChildItem "$VAM_DIR\software\Peformace Patches\V10.2_*.7z" -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
$script:patchCycle = @(
    @{
        Name        = "v10.2"
        Zip         = $_v102zip
        AsmZipPath  = "Assembly-CSharp.dll"
        SkinZipPath = "PerformancePatches\SkinMeshPartDLL.dll"
        IniZipPath  = "PerformancePatches\SkinMeshPartDLL.ini"
        StashDir    = "$PATCH_STASH\v10.2"
        AsmCRC      = 1337572448
        SkinCRC     = 3891736159
    }
    @{
        Name        = "v12"
        Zip         = "$PATCH_DIR\Version 12.zip"
        AsmZipPath  = "patched12/VaM_Data/Managed/Assembly-CSharp.dll"
        SkinZipPath = "patched12/PerformancePatches/SkinMeshPartDLL.dll"
        IniZipPath  = "patched12/PerformancePatches/SkinMeshPartDLL.ini"
        StashDir    = "$PATCH_STASH\v12"
        AsmCRC      = 3715869950
        SkinCRC     = 153640169
    }
    @{
        Name        = "v12evo"
        Zip         = "$PATCH_DIR\Version 12evo.zip"
        AsmZipPath  = "VaM_Data/Managed/Assembly-CSharp.dll"
        SkinZipPath = "PerformancePatches/SkinMeshPartDLL.dll"
        IniZipPath  = "PerformancePatches/SkinMeshPartDLL.ini"
        StashDir    = "$PATCH_STASH\v12evo"
        AsmCRC      = 437968350
        SkinCRC     = 153640169
    }
    @{
        Name        = "v13beta1"
        Zip         = "$PATCH_DIR\Version 13beta1.zip"
        AsmZipPath  = "VaM_Data/Managed/Assembly-CSharp.dll"
        SkinZipPath = "PerformancePatches/SkinMeshPartDLL.dll"
        IniZipPath  = "PerformancePatches/SkinMeshPartDLL.ini"
        StashDir    = "$PATCH_STASH\v13beta1"
        AsmCRC      = 1252404939
        SkinCRC     = 3891736159
    }
    @{
        Name        = "v13beta1evo"
        Zip         = "$PATCH_DIR\patched13beta1evo.zip"
        AsmZipPath  = "VaM_Data/Managed/Assembly-CSharp.dll"
        SkinZipPath = "PerformancePatches/SkinMeshPartDLL.dll"
        IniZipPath  = "PerformancePatches/SkinMeshPartDLL.ini"
        StashDir    = "$PATCH_STASH\v13beta1evo"
        AsmCRC      = 1486114389
        SkinCRC     = 3891736159
    }
)

$script:patchDesc = @{
    "v10.2"       = "v10.2 CPU Performance Patch (VaM 1.22.0.x)"
    "v12"         = "Version 12 (VaM 1.22.0.3)  [NO SECURITY PATCH]`nMaxPerChar: fewer threads with many chars, all threads with 1 char. CPU runs 100% with 1 char/300fps."
    "v12evo"      = "Version 12evo (VaM 1.22.0.12 / 1.22.0.13)  [RECOMMENDED if v13 is unstable]`nContains security fixes from latest VaM patches. Otherwise identical to Version 12."
    "v13beta1"    = "Version 13beta1 (VaM 1.22.0.3)  [UNSTABLE FOR SOME USERS  --  NO SECURITY PATCH]`nengineAffinity param: list cores to reserve for Unity (use your 2 fastest, Ryzen Master helps). Delete param to disable."
    "v13beta1evo" = "Version 13beta1evo (VaM 1.22.0.12 / 1.22.0.13)  [UNSTABLE FOR SOME USERS]`nContains security fixes from latest VaM patches. Otherwise identical to Version 13beta1."
}

# EXE profiles: name -> (exe, data folder, process name)
$script:profiles = @{
    "VaM"  = @{ Exe = "$VAM_DIR\VaM.exe";  Data = "$VAM_DIR\VaM_Data";  Proc = "VaM"  }
    "SotR" = @{ Exe = "$VAM_DIR\sotr.exe"; Data = "$VAM_DIR\sotr_Data"; Proc = "sotr" }
}
$PROFILE_FILE = "$LOG_DIR\last_profile_steam.txt"
$script:activeProfile = "VaM"
if ((Test-Path $PROFILE_FILE) -and ((Get-Content $PROFILE_FILE -Raw).Trim() -in $script:profiles.Keys)) {
    $script:activeProfile = (Get-Content $PROFILE_FILE -Raw).Trim()
}

if (!(Test-Path "$VAM_DIR\VaM.exe")) {
    [System.Windows.Forms.MessageBox]::Show("VaM.exe not found in $VAM_DIR")
    exit
}

if (!(Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR | Out-Null
}

# =================================================
# GUI SETUP
# =================================================
$form = New-Object System.Windows.Forms.Form
$form.Text = "VaM  //  NEURAL CORE ACTIVE"
$form.StartPosition = "CenterScreen"
$form.Size = New-Object System.Drawing.Size(582, 792)

# =================================================
# BACKGROUND IMAGE SYSTEM
# =================================================
$script:bgImages = @()
$script:bgIndex = -1
$script:bgAutoRotate = $true
$script:bgFirstSize = $null

$allBgFiles = @()
foreach ($dir in @($BG_FOLDER, $BG_EXTRA)) {
    if (Test-Path $dir) {
        $allBgFiles += @(Get-ChildItem $dir -Recurse -File | Where-Object {
            $_.Extension -match "\.(jpg|jpeg|png|bmp|gif|webp)$"
        })
    }
}
if ($allBgFiles.Count -gt 0) {
    $script:bgImages = @($allBgFiles | Get-Random -Count ([int]::MaxValue))  # shuffle
}

function Set-BackgroundImage {
    if ($script:bgImages.Count -eq 0) { return }
    $script:bgIndex = ($script:bgIndex + 1) % $script:bgImages.Count
    $file = $script:bgImages[$script:bgIndex]
    $newImg = [System.Drawing.Image]::FromFile($file.FullName)
    $newImg.RotateFlip([System.Drawing.RotateFlipType]::RotateNoneFlipX)
    if ($script:bgFirstSize -eq $null) {
        $script:bgFirstSize = New-Object System.Drawing.Size($newImg.Width, $newImg.Height)
    }
    $oldImg = $form.BackgroundImage
    $form.BackgroundImage = $newImg
    $form.BackgroundImageLayout = "Stretch"
    if ($oldImg -ne $null) { $oldImg.Dispose() }
}

Set-BackgroundImage

# =================================================
# SIDE PANEL (buttons on the right)
# =================================================
$sideW = 140
$panel = New-Object System.Windows.Forms.Panel
$panel.Width = $sideW
$panel.Dock = "Right"
$panel.BackColor = [System.Drawing.Color]::FromArgb(180,40,40,40)
$form.Controls.Add($panel)

$btnH = 30
$btnW = $sideW - 10
$btnX = 5
$btnY = 5
$btnGap = 34

function New-SideButton($text, $fgColor) {
    $btn = New-Object System.Windows.Forms.Button
    $btn.Text = $text
    $btn.Width = $script:btnW
    $btn.Height = $script:btnH
    $btn.Left = $script:btnX
    $btn.Top = $script:btnY
    $btn.ForeColor = $fgColor
    $btn.BackColor = [System.Drawing.Color]::FromArgb(200,60,60,60)
    $btn.FlatStyle = "Flat"
    $btn.Font = New-Object System.Drawing.Font("Segoe UI", 8)
    $panel.Controls.Add($btn)
    $script:btnY += $script:btnGap
    return $btn
}

$btnRestart  = New-SideButton "Kill + Restart" ([System.Drawing.Color]::White)
$btnKillOnly = New-SideButton "Kill Only"      ([System.Drawing.Color]::Yellow)
$btnExit     = New-SideButton "Hard Exit"       ([System.Drawing.Color]::Red)

# Separator
$script:btnY += 6

$btnSwitch = New-SideButton "Switch: $($script:activeProfile)" $(if ($script:activeProfile -eq "VaM") { [System.Drawing.Color]::Cyan } else { [System.Drawing.Color]::Orange })

# Separator
$script:btnY += 6

$btnNextImg = New-SideButton "Next Img" ([System.Drawing.Color]::LightGreen)
$btnAutoImg = New-SideButton "Auto Img: ON" ([System.Drawing.Color]::LightGreen)

# Detect current mono state
function Get-MonoState {
    if (!(Test-Path $MONO_CURRENT)) { return "unknown" }
    $crc = [Crc32]::Compute($MONO_CURRENT)
    if ($crc -eq $MONO_CRC_PATCHED) { return "3x Heap" }
    if ($crc -eq $MONO_CRC_DEFAULT) { return "Default" }
    return "unknown"
}

$script:monoState = Get-MonoState

# Separator
$script:btnY += 6

$btnMono = New-SideButton "Mono: $($script:monoState)" $(if ($script:monoState -eq "3x Heap") { [System.Drawing.Color]::Orange } else { [System.Drawing.Color]::White })

# ASM patch detection via CRC32 (cycles: Stock -> v10.2 -> v12 -> v12evo -> v13beta1 -> v13beta1evo -> Stock)
function Get-AsmState {
    $current = "$($ASM_DIRS[0])\Assembly-CSharp.dll"
    if (!(Test-Path $current)) { return "Stock" }
    $crc = [Crc32]::Compute($current)
    foreach ($p in $script:patchCycle) {
        if ($p.AsmCRC -eq $crc) { return $p.Name }
    }
    return "Stock"
}

function Get-AsmColor($state) {
    switch ($state) {
        "v10.2"       { return "Lime"    }
        "v12"         { return "Yellow"  }
        "v12evo"      { return "Orange"  }
        "v13beta1"    { return "Cyan"    }
        "v13beta1evo" { return "Magenta" }
        default       { return "White"   }
    }
}

function Invoke-StockAsm {
    $def0 = "$($ASM_STASH[0])\Assembly-CSharp.default.dll"
    $def1 = "$($ASM_STASH[1])\Assembly-CSharp.default.dll"
    if (Test-Path $def0) { Copy-Item $def0 "$($ASM_DIRS[0])\Assembly-CSharp.dll" -Force }
    if (Test-Path $def1) { Copy-Item $def1 "$($ASM_DIRS[1])\Assembly-CSharp.dll" -Force }
    if (Test-Path "$PERF_DIR\SkinMeshPartDLL.dll") {
        Rename-Item "$PERF_DIR\SkinMeshPartDLL.dll" "SkinMeshPartDLL.dll.disabled" -Force
    }
    Write-Log "[>] ASM: STOCK (VaM + SotR) [<]" "White"
    return $true
}

function Invoke-Patch($p) {
    $stashAsm = "$($p.StashDir)\Assembly-CSharp.dll"
    if (!(Test-Path $stashAsm)) {
        if (!(Test-Path $p.Zip)) {
            Write-Log "Archive not found: $($p.Zip)" "Red"
            return $false
        }
        New-Item -ItemType Directory -Path $p.StashDir -Force | Out-Null
        if ($p.Zip.ToLower().EndsWith('.7z')) {
            $7zExe = "C:\Program Files\7-Zip\7z.exe"
            if (!(Test-Path $7zExe)) {
                Write-Log "7-Zip not found at $7zExe" "Red"
                return $false
            }
            Write-Log "Extracting $($p.Name) from 7z..." "Cyan"
            foreach ($entry in @($p.AsmZipPath, $p.SkinZipPath, $p.IniZipPath) | Where-Object { $_ }) {
                & $7zExe e $p.Zip $entry -o"$($p.StashDir)" -y | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    Write-Log "7z failed to extract: $entry" "Red"
                    return $false
                }
            }
        } else {
            Write-Log "Extracting $($p.Name) from zip..." "Cyan"
            $zip = [System.IO.Compression.ZipFile]::OpenRead($p.Zip)
            foreach ($entry in $zip.Entries) {
                if ($entry.FullName -eq $p.AsmZipPath) {
                    [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $stashAsm, $true)
                }
                if ($entry.FullName -eq $p.SkinZipPath) {
                    [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, "$($p.StashDir)\SkinMeshPartDLL.dll", $true)
                }
                if ($entry.FullName -eq $p.IniZipPath) {
                    [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, "$($p.StashDir)\SkinMeshPartDLL.ini", $true)
                }
            }
            $zip.Dispose()
        }
        $extractedCRC = [Crc32]::Compute($stashAsm)
        if ($extractedCRC -ne $p.AsmCRC) {
            Write-Log "CRC MISMATCH from archive! Expected $($p.AsmCRC) got $extractedCRC -- archive may be corrupt." "Red"
            return $false
        }
        Write-Log "$($p.Name) extracted and CRC verified." "Green"
    }
    Copy-Item $stashAsm "$($ASM_DIRS[0])\Assembly-CSharp.dll" -Force
    $sotrDef = "$($ASM_STASH[1])\Assembly-CSharp.default.dll"
    if (Test-Path $sotrDef) { Copy-Item $sotrDef "$($ASM_DIRS[1])\Assembly-CSharp.dll" -Force }
    $stashSkin = "$($p.StashDir)\SkinMeshPartDLL.dll"
    if (Test-Path $stashSkin) {
        if (Test-Path "$PERF_DIR\SkinMeshPartDLL.dll.disabled") {
            Remove-Item "$PERF_DIR\SkinMeshPartDLL.dll.disabled" -Force -Confirm:$false
        }
        Copy-Item $stashSkin "$PERF_DIR\SkinMeshPartDLL.dll" -Force
        $stashIni = "$($p.StashDir)\SkinMeshPartDLL.ini"
        if (Test-Path $stashIni) { Copy-Item $stashIni "$PERF_DIR\SkinMeshPartDLL.ini" -Force }
    }
    $appliedCRC = [Crc32]::Compute("$($ASM_DIRS[0])\Assembly-CSharp.dll")
    if ($appliedCRC -ne $p.AsmCRC) {
        Write-Log "CRC MISMATCH after apply for $($p.Name)! Got $appliedCRC" "Red"
        return $false
    }
    Write-Log "[>] ASM: $($p.Name) applied -- CRC OK [<]" (Get-AsmColor $p.Name)
    if ($script:patchDesc -and $script:patchDesc.ContainsKey($p.Name)) {
        foreach ($line in $script:patchDesc[$p.Name].Split("`n")) { Write-Log "  $line" "DarkGray" }
    }
    return $true
}

function Update-AsmButton {
    $state = Get-AsmState
    $btnAsm.Text = "ASM: $state"
    $colorName = Get-AsmColor $state
    $btnAsm.ForeColor = [System.Drawing.Color]::$colorName
    if ($script:asmTooltip) {
        $desc = if ($script:patchDesc -and $script:patchDesc.ContainsKey($state)) { $script:patchDesc[$state] } else { "Assembly-CSharp patch  (click to cycle)" }
        $script:asmTooltip.SetToolTip($btnAsm, $desc)
    }
}

# Load persisted auto-launch setting
$script:autoLaunch = $true
if (Test-Path "$LOG_DIR\auto_launch_steam.txt") {
    $val = (Get-Content "$LOG_DIR\auto_launch_steam.txt" -Raw).Trim()
    if ($val -eq "false") { $script:autoLaunch = $false }
}

$btnAutoLaunch  = New-SideButton $(if ($script:autoLaunch) { "Launch: ON" } else { "Launch: OFF" }) $(if ($script:autoLaunch) { [System.Drawing.Color]::LightGreen } else { [System.Drawing.Color]::Gray })
$btnAutoRestart = New-SideButton "AutoR: ON" ([System.Drawing.Color]::LightGreen)

$btnAsm = New-SideButton "ASM: ..." ([System.Drawing.Color]::White)
$script:asmTooltip = New-Object System.Windows.Forms.ToolTip
$script:asmTooltip.AutoPopDelay = 30000
$script:asmTooltip.InitialDelay = 400
$script:asmTooltip.ShowAlways   = $true
Update-AsmButton

# OpenVR FSR detection
function Get-FsrState {
    $fsrDll = "$FSR_STASH\openvr_api.dll"
    if (!(Test-Path $fsrDll)) { return "N/A" }
    $currentSize = (Get-Item "$($PLUGIN_DIRS[0])\openvr_api.dll").Length
    $fsrSize = (Get-Item $fsrDll).Length
    if ($currentSize -eq $fsrSize) { return "ON" }
    return "OFF"
}

function Update-FsrButton {
    $state = Get-FsrState
    $btnFsr.Text = "FSR: $state"
    $btnFsr.ForeColor = $(if ($state -eq "ON") { [System.Drawing.Color]::Lime } elseif ($state -eq "N/A") { [System.Drawing.Color]::Gray } else { [System.Drawing.Color]::White })
}

$btnFsr = New-SideButton "FSR: ..." ([System.Drawing.Color]::White)
Update-FsrButton

function Get-BepInExState {
    if (!(Test-Path $BEPINEX_DLL)) { return "OFF" }
    $crc = [Crc32]::Compute($BEPINEX_DLL)
    if ($crc -eq $BEPINEX_CRC_X64)    { return "x64 v23" }
    if ($crc -eq $BEPINEX_CRC_X86)    { return "x86 v23" }
    if ($crc -eq $BEPINEX_CRC_X64_21) { return "x64 v21" }
    if ($crc -eq $BEPINEX_CRC_X86_21) { return "x86 v21" }
    return "Other"
}

function Update-BepInExButton {
    $state = Get-BepInExState
    $btnBepInEx.Text = "BepInEx: $state"
    if      ($state -eq "x64 v23") { $btnBepInEx.ForeColor = [System.Drawing.Color]::Cyan   }
    elseif  ($state -eq "x86 v23") { $btnBepInEx.ForeColor = [System.Drawing.Color]::Yellow }
    elseif  ($state -eq "x64 v21") { $btnBepInEx.ForeColor = [System.Drawing.Color]::Lime   }
    elseif  ($state -eq "x86 v21") { $btnBepInEx.ForeColor = [System.Drawing.Color]::Orange }
    elseif  ($state -eq "Other")   { $btnBepInEx.ForeColor = [System.Drawing.Color]::Red    }
    else                           { $btnBepInEx.ForeColor = [System.Drawing.Color]::White  }
}

$btnBepInEx = New-SideButton "BepInEx: ..." ([System.Drawing.Color]::White)
Update-BepInExButton

# Separator
$script:btnY += 6

$ADDON_ROOT  = "$VAM_DIR\AddonPackages"
$RANDMOD_STATE = "$ADDON_ROOT\.vam_random_toggle_state.json"
$MODEL_STATE = "$ADDON_ROOT\.vam_model_toggle_state.json"

function Find-MarkerDir($MarkerFile) {
    $hit = Get-ChildItem -Path $ADDON_ROOT -Recurse -File -Filter $MarkerFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($hit) { return $hit.DirectoryName }
    return $null
}

function Get-MetaDependencies($VarPath) {
    try {
        $zip = [System.IO.Compression.ZipFile]::OpenRead($VarPath)
        $entry = $zip.GetEntry("meta.json")
        if (!$entry) { $zip.Dispose(); return $null }
        $sr = New-Object IO.StreamReader($entry.Open())
        $json = $sr.ReadToEnd()
        $sr.Close()
        $zip.Dispose()
        return ($json | ConvertFrom-Json).dependencies
    } catch { return $null }
}

function Split-PackageKey($Key) {
    $idx = $Key.LastIndexOf('.')
    if ($idx -lt 0) { return $null }
    [PSCustomObject]@{ Prefix = $Key.Substring(0, $idx); Version = $Key.Substring($idx + 1) }
}

function Build-RandModIndex {
    $files = Get-ChildItem -Path $ADDON_ROOT -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -ieq ".var" -or $_.Extension -ieq ".DISABLED" }
    $index = @{}
    foreach ($f in $files) {
        $baseName = [IO.Path]::GetFileNameWithoutExtension($f.Name)
        $lastDot = $baseName.LastIndexOf('.')
        if ($lastDot -lt 0) { continue }
        $prefix = $baseName.Substring(0, $lastDot)
        $verStr = $baseName.Substring($lastDot + 1)
        $verNum = 0
        if (![int]::TryParse($verStr, [ref]$verNum)) { continue }
        $key = $prefix.ToLowerInvariant()
        if (!$index.ContainsKey($key)) { $index[$key] = @() }
        $index[$key] += [PSCustomObject]@{ Version = $verNum; Path = $f.FullName; Enabled = ($f.Extension -ieq ".var") }
    }
    return $index
}

function Find-RandModBestFile($Index, $Prefix, $VersionToken) {
    $key = $Prefix.ToLowerInvariant()
    if (!$Index.ContainsKey($key)) { return $null }
    # Always take the highest-numbered .var/.DISABLED on disk for this package,
    # regardless of whether the dependency lists "latest" or a specific version.
    return ($Index[$key] | Sort-Object Version -Descending | Select-Object -First 1)
}

function Resolve-RandModDependencies($Index, $DepsObj, $Visited, $Results) {
    if (!$DepsObj) { return }
    foreach ($prop in $DepsObj.PSObject.Properties) {
        $parsed = Split-PackageKey $prop.Name
        if (!$parsed) { continue }
        $prefixKey = $parsed.Prefix.ToLowerInvariant()
        if ($Visited.ContainsKey($prefixKey)) {
            Resolve-RandModDependencies $Index $prop.Value.dependencies $Visited $Results
            continue
        }
        $Visited[$prefixKey] = $true
        $file = Find-RandModBestFile $Index $parsed.Prefix $parsed.Version
        if ($file) {
            $Results.Add($file) | Out-Null
            if ($file.Path -match '\.var$') {
                Resolve-RandModDependencies $Index (Get-MetaDependencies $file.Path) $Visited $Results
            }
        } else {
            Write-Log "  (warning) dependency not found: $($prop.Name)" "DarkGray"
        }
        Resolve-RandModDependencies $Index $prop.Value.dependencies $Visited $Results
    }
}

function Enable-RandModFile($Path, [bool]$ResetDate = $false) {
    if ($Path -match '\.DISABLED$') {
        $newPath = $Path.Substring(0, $Path.Length - ".DISABLED".Length) + ".var"
        Rename-Item -LiteralPath $Path -NewName (Split-Path $newPath -Leaf) -ErrorAction Stop
        if ($ResetDate) {
            $now = Get-Date
            Set-ItemProperty -LiteralPath $newPath -Name LastWriteTime -Value $now
            Set-ItemProperty -LiteralPath $newPath -Name CreationTime -Value $now
            Set-ItemProperty -LiteralPath $newPath -Name LastAccessTime -Value $now
        }
        return $newPath
    }
    return $Path
}

function Disable-RandModFile($Path) {
    if ($Path -match '\.var$' -and (Test-Path -LiteralPath $Path)) {
        $newPath = $Path.Substring(0, $Path.Length - ".var".Length) + ".DISABLED"
        Rename-Item -LiteralPath $Path -NewName (Split-Path $newPath -Leaf) -ErrorAction Stop
        return $newPath
    }
    return $Path
}

function Invoke-RandomToggle($MarkerFile, $StateFile, $Label, $Button, $OtherStateFile) {
    Write-Log "" "White"
    Write-Log "[>] $Label TOGGLE [<]" "Magenta"

    $SourceDir = Find-MarkerDir $MarkerFile
    if (!$SourceDir) {
        Write-Log "  Could not find a folder containing $MarkerFile under AddonPackages" "Red"
        return
    }

    # Files the other toggle currently has enabled -- never disable these, even if
    # they were originally enabled by this toggle (e.g. a shared dependency).
    $otherProtected = @{}
    if ($OtherStateFile -and (Test-Path -LiteralPath $OtherStateFile)) {
        try {
            $otherState = Get-Content -LiteralPath $OtherStateFile -Raw | ConvertFrom-Json
            foreach ($p in $otherState.EnabledFiles) { $otherProtected[$p] = $true }
        } catch {}
    }

    if (Test-Path -LiteralPath $StateFile) {
        try {
            $prevState = Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json
            foreach ($p in $prevState.EnabledFiles) {
                if ($otherProtected.ContainsKey($p)) {
                    Write-Log "  Keeping enabled (shared with other toggle): $(Split-Path $p -Leaf)" "DarkGray"
                    continue
                }
                Disable-RandModFile $p | Out-Null
            }
            Write-Log "  Reverted: $($prevState.MainPackage)" "DarkGray"
        } catch {
            Write-Log "  Could not fully revert previous state: $_" "Red"
        }
        Remove-Item -LiteralPath $StateFile -ErrorAction SilentlyContinue
    }

    $candidates = Get-ChildItem -Path $SourceDir -Recurse -File -Filter "*.DISABLED" -ErrorAction SilentlyContinue
    if (!$candidates -or $candidates.Count -eq 0) {
        Write-Log "  No *.DISABLED packages left in $SourceDir" "Red"
        return
    }
    $chosen = Get-Random -InputObject $candidates

    Write-Log "  Indexing AddonPackages..." "DarkGray"
    $index = Build-RandModIndex
    $visited = @{}
    $results = New-Object System.Collections.Generic.List[Object]

    $baseName = [IO.Path]::GetFileNameWithoutExtension($chosen.Name)
    $lastDot = $baseName.LastIndexOf('.')
    $mainPrefix = $baseName.Substring(0, $lastDot)
    $visited[$mainPrefix.ToLowerInvariant()] = $true

    Resolve-RandModDependencies $index (Get-MetaDependencies $chosen.FullName) $visited $results

    $enabledPaths = New-Object System.Collections.Generic.List[String]
    $newMainPath = Enable-RandModFile $chosen.FullName $true
    if ($newMainPath -ne $chosen.FullName) { $enabledPaths.Add($newMainPath) }
    foreach ($dep in $results) {
        if (!$dep.Enabled) {
            $newPath = Enable-RandModFile $dep.Path $false
            if ($newPath -ne $dep.Path) { $enabledPaths.Add($newPath) }
        }
    }

    $state = [PSCustomObject]@{ MainPackage = $baseName; EnabledFiles = $enabledPaths }
    $state | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StateFile -Encoding UTF8

    Write-Log "  Enabled: $baseName" "Lime"
    Write-Log "  Plus $($enabledPaths.Count - 1) dependency package(s)." "Lime"
    $Button.Text = "$Label`: $baseName".Substring(0, [Math]::Min(22, "$Label`: $baseName".Length))
}

$QVARO_EXE  = "$VAM_DIR\Qvaro 1.7.0.exe"
$QVARO_NAME = 'Qvaro 1.7.0'

function Get-QvaroState {
    if (@(Get-Process -Name $QVARO_NAME -ErrorAction SilentlyContinue).Count -gt 0) { return "ON" }
    return "OFF"
}

function Update-QvaroButton {
    $state = Get-QvaroState
    $btnQvaro.Text      = "Qvaro: $state"
    $btnQvaro.ForeColor = $(if ($state -eq "ON") { [System.Drawing.Color]::Lime } else { [System.Drawing.Color]::Gray })
}

$btnQvaro = New-SideButton "Qvaro: ..." ([System.Drawing.Color]::Gray)
Update-QvaroButton

# Separator
$script:btnY += 6

$btnRandomMod = New-SideButton "Random Mod" ([System.Drawing.Color]::Magenta)
$btnModel     = New-SideButton "Model" ([System.Drawing.Color]::Magenta)

# =================================================
# LOG BOX
# =================================================
$logBox = New-Object System.Windows.Forms.RichTextBox
$logBox.Dock = "Bottom"
$logBox.Height = 180
$logBox.ReadOnly = $true
$logBox.BackColor = "Black"
$logBox.ForeColor = "White"
$logBox.Font = New-Object System.Drawing.Font("Consolas",10)
$form.Controls.Add($logBox)

# =================================================
# LOG FUNCTION
# =================================================
function Write-Log($msg, $color="White") {
    $logBox.SelectionStart = $logBox.TextLength
    $logBox.SelectionLength = 0
    $logBox.SelectionColor = [System.Drawing.Color]::$color
    $logBox.AppendText("[$(Get-Date -Format HH:mm:ss)] $msg`n")
    $logBox.SelectionColor = $logBox.ForeColor
    $logBox.ScrollToCaret()
}

# =================================================
# PREFS FORCE
# =================================================
function Force-Prefs {
    if (Test-Path $PREFS_FILE) {
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        Copy-Item $PREFS_FILE "$LOG_DIR\prefs.json.backup_$timestamp"
        Write-Log "Backed up prefs.json" "Yellow"
    }

    Write-Log "Writing optimized FAST navigation prefs..." "Cyan"

@"
{
  "firstTimeUser": false,
  "renderScale": 1.15,
  "msaaLevel": 0,
  "desktopVsync": false,
  "pixelLightCount": 2,
  "shaderLOD": "Medium",
  "smoothPasses": 1,
  "mirrorReflections": false,
  "realtimeReflectionProbes": false,
  "mirrorToDisplay": false,
  "glowEffects": "Medium",
  "generateDepthTexture": false,
  "overlayUI": true,
  "VRUISide": "Left",
  "monitorUIScale": 0.85,
  "monitorUIYOffset": -6,
  "targetAlpha": 0.8,
  "crosshairAlpha": 0.04,
  "physicsRate": "_90",
  "physicsUpdateCap": 2,
  "physicsHighQuality": false,
  "softBodyPhysics": true,
  "cpuPhysicsOptimization": false,
  "optimizeMemoryOnSceneLoad": true,
  "optimizeMemoryOnPresetLoad": false,
  "enableCaching": true,
  "disableTeleportDuringPossess": false,
  "teleportAllowRotation": true,
  "freeMoveMultiplier": 9.0,
  "grabNavigationPositionMultiplier": 5.5,
  "grabNavigationRotationMultiplier": 2.5,
  "allowPossessSpringAdjustment": true,
  "possessPositionSpring": 12000,
  "possessRotationSpring": 1400,
  "oculusThumbstickFunction": "GrabWorld",
  "motionControllerUseCollision": false,
  "motionControllerLinkHands": true,
  "cacheFolder": "${ROOT}\\Cache",
  "enableWebBrowser": true,
  "allowNonWhitelistDomains": true,
  "enableWebBrowserProfile": true,
  "enableWebMisc": true,
  "enableHub": true,
  "enableHubDownloader": true,
  "enablePlugins": true,
  "allowPluginsNetworkAccess": true,
  "alwaysAllowPluginsDownloadedFromHub": true,
  "hideDisabledWebMessages": true,
  "confirmLoad": false,
  "termsOfUseAccepted": true,
  "creatorName": "Milkbaron",
  "fileBrowserSortBy": "NewToOld",
  "fileBrowserDirectoryOption": "ShowLast"
}
"@ | Set-Content $PREFS_FILE

    Write-Log "prefs.json enforced." "Green"

    # Force AllFlattenedFirst config - set all Flatten to true
    $affCfg = "$VAM_DIR\BepInEx\config\com.virtamate.vamplugins.allflattenedfirst.cfg"
    if (Test-Path $affCfg) {
        $cfgText = Get-Content $affCfg -Raw
        $cfgText = $cfgText -replace '(Flatten:\s+\S.*?=\s*)false', '${1}true'
        Set-Content $affCfg $cfgText -NoNewline
        Write-Log "AllFlattenedFirst: all Flatten set to true." "Green"
    }
}

# =================================================
# DXGI
# =================================================
function Disable-DXGI {
    if (Test-Path $ROOT_DXGI) {
        Rename-Item $ROOT_DXGI "dxgi.disabled" -Force
        Write-Log "dxgi.dll disabled." "Magenta"
    }
}

function Restore-DXGI {
    if (Test-Path $DXGI_DISABLED) {
        Rename-Item $DXGI_DISABLED "dxgi.dll" -Force
        Write-Log "dxgi.dll restored." "Magenta"
    }
}

# =================================================
# ISLC
# =================================================
function Start-ISLC {
    if (Test-Path $ISLC_EXE) {
        $running = Get-Process "Intelligent standby list cleaner ISLC" -ErrorAction SilentlyContinue
        if (!$running) {
            Start-Process $ISLC_EXE
            Write-Log "ISLC started." "Blue"
        } else {
            Write-Log "ISLC already running." "Blue"
        }
    }
}

function Kill-ISLC {
    taskkill /f /im "Intelligent standby list cleaner ISLC.exe" 2>$null | Out-Null
    Write-Log "ISLC killed." "Blue"
}

# =================================================
# RAM DISK
# =================================================
function Setup-RamDisk {
    Write-Log "Checking Z:\Zaje..." "White"

    if (Test-Path "$ZAJE_DST\") {
        Write-Log "Z:\Zaje present -- skipping." "Green"
        return
    }

    if (!(Test-Path "Z:\")) {
        if (!(Test-Path $RAMDISK_EXE)) {
            Write-Log "RAM Disk exe not found -- skipping." "Red"
            return
        }
        Start-Process $RAMDISK_EXE
        Write-Log "Waiting for Z:\ to mount..." "White"
        $waited = 0
        while (!(Test-Path "Z:\") -and $waited -lt 30) {
            Start-Sleep 1
            $waited++
        }
        if (!(Test-Path "Z:\")) {
            Write-Log "Z:\ timed out after 30s." "Red"
            return
        }
        Write-Log "Z:\ mounted." "Green"
    }

    Write-Log "Copying Zaje to Z:\Zaje..." "White"
    robocopy $ZAJE_SRC $ZAJE_DST /E /Z /NP /NJH /NJS | Out-Null
    Write-Log "Zaje copy complete." "Green"
}

# =================================================
# VAM CONTROL
# =================================================
$script:vamProcess = $null
$script:autoRestart = $true
$script:sessionCount = 0
$script:launchTime = $null

function Start-VaM {
    $p = $script:profiles[$script:activeProfile]
    $script:sessionCount++
    $script:launchTime = Get-Date
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Write-Log "-------------------------------------" "DarkGray"
    Write-Log "SESSION #$($script:sessionCount) INIT" "Cyan"
    Write-Log "  Profile : $($script:activeProfile)" "White"
    Write-Log "  Binary  : $($p.Exe)" "DarkGray"
    Write-Log "  Mode    : Steam VR" "DarkGray"
    Add-Content $SESSION_LOG "[$timestamp] START $($script:activeProfile) [#$($script:sessionCount)]"
    Force-Prefs
    Disable-DXGI
    if ($script:activeProfile -eq "VaM") {
        Start-Process $STEAM_URI
        Write-Log "  Launch  : Steam URI" "Green"
    } else {
        $script:vamProcess = Start-Process $p.Exe -ArgumentList "-vrmode openvr" -WorkingDirectory $VAM_DIR -PassThru
        Write-Log "  PID     : $($script:vamProcess.Id)" "Green"
    }
    Start-ISLC
    Write-Log "  Status  : RUNNING" "Green"
    Write-Log "-------------------------------------" "DarkGray"
}

function Get-Uptime {
    if ($script:launchTime) {
        $span = (Get-Date) - $script:launchTime
        return "{0:D2}h {1:D2}m {2:D2}s" -f [int]$span.TotalHours, $span.Minutes, $span.Seconds
    }
    return "N/A"
}

function Kill-VaM {
    $uptime = Get-Uptime
    $p = $script:profiles[$script:activeProfile]
    # Grab mem before kill
    $proc = Get-Process $p.Proc -ErrorAction SilentlyContinue | Select-Object -First 1
    $memMB = if ($proc) { [math]::Round($proc.WorkingSet64 / 1MB) } else { "?" }

    # Kill by process name
    foreach ($prof in $script:profiles.Values) {
        try { Get-Process $prof.Proc -ErrorAction Stop | Stop-Process -Force } catch {}
    }

    # Also kill by PID if we have it
    if ($script:vamProcess -ne $null -and !$script:vamProcess.HasExited) {
        try { $script:vamProcess.Kill() } catch {}
    }

    # Fallback: taskkill by exe name (catches cases where process name doesn't match)
    try { taskkill /f /im "VaM.exe" 2>$null } catch {}
    try { taskkill /f /im "sotr.exe" 2>$null } catch {}

    $script:vamProcess = $null

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Write-Log "TERMINATED  $($script:activeProfile)  [uptime $uptime | peak ${memMB}MB RAM]" "Red"
    Add-Content $SESSION_LOG "[$timestamp] KILLED $($script:activeProfile) [uptime $uptime]"
    Restore-DXGI
}

# =================================================
# TIMER - monitor VaM process for auto-restart
# =================================================
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 2000
$timer.Add_Tick({
    $p = $script:profiles[$script:activeProfile]
    $running = Get-Process $p.Proc -ErrorAction SilentlyContinue
    if ($script:autoRestart -and $script:launchTime -and !$running -and ((Get-Date) - $script:launchTime).TotalSeconds -gt 15) {
        $uptime = Get-Uptime
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        Write-Log "$($script:activeProfile) exited after $uptime -- cycling..." "Yellow"
        Add-Content $SESSION_LOG "[$timestamp] CLOSED $($script:activeProfile) [uptime $uptime]"
        Restore-DXGI
        Start-Sleep 3
        Start-VaM
    }
    # Live title bar stats
    $p = $script:profiles[$script:activeProfile]
    $proc = Get-Process $p.Proc -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($proc) {
        $memGB = [math]::Round($proc.WorkingSet64 / 1GB, 1)
        $uptime = Get-Uptime
        $form.Text = "$($script:activeProfile) Steam  //  ${memGB}GB RAM  //  $uptime  //  Session #$($script:sessionCount)"
    } else {
        $form.Text = "$($script:activeProfile) Steam  //  WAITING..."
    }
    Update-QvaroButton
})
$timer.Start()

# =================================================
# BUTTON EVENTS
# =================================================
$btnRestart.Add_Click({
    $script:autoRestart = $true
    $btnAutoRestart.Text = "AutoR: ON"
    $btnAutoRestart.ForeColor = [System.Drawing.Color]::LightGreen
    Write-Log "" "White"
    Write-Log "[>] KILL SIGNAL SENT [<]" "Yellow"
    Kill-VaM
    Write-Log "   Cooling down (3s)..." "DarkGray"
    Start-Sleep 3
    Write-Log "[>] RESPAWNING [<]" "Cyan"
    Start-VaM
})

$btnKillOnly.Add_Click({
    $script:autoRestart = $false
    $btnAutoRestart.Text = "AutoR: OFF"
    $btnAutoRestart.ForeColor = [System.Drawing.Color]::Gray
    Write-Log "" "White"
    Write-Log "[>] KILL (no restart) [<]" "Yellow"
    Kill-VaM
    Write-Log "   Auto-restart PAUSED. Hit Kill+Restart to relaunch." "DarkGray"
})

$btnAutoLaunch.Add_Click({
    $script:autoLaunch = !$script:autoLaunch
    if ($script:autoLaunch) {
        $btnAutoLaunch.Text = "Launch: ON"
        $btnAutoLaunch.ForeColor = [System.Drawing.Color]::LightGreen
        Write-Log "Auto-launch ON" "Green"
    } else {
        $btnAutoLaunch.Text = "Launch: OFF"
        $btnAutoLaunch.ForeColor = [System.Drawing.Color]::Gray
        Write-Log "Auto-launch OFF" "Yellow"
    }
    # Persist
    $val = if ($script:autoLaunch) { "true" } else { "false" }
    $val | Set-Content "$LOG_DIR\auto_launch_steam.txt"
})

$btnAutoRestart.Add_Click({
    $script:autoRestart = !$script:autoRestart
    if ($script:autoRestart) {
        $btnAutoRestart.Text = "AutoR: ON"
        $btnAutoRestart.ForeColor = [System.Drawing.Color]::LightGreen
        Write-Log "[>] Auto-restart ENABLED [<]" "Green"
    } else {
        $btnAutoRestart.Text = "AutoR: OFF"
        $btnAutoRestart.ForeColor = [System.Drawing.Color]::Gray
        Write-Log "[>] Auto-restart DISABLED [<]" "Yellow"
    }
})

$btnExit.Add_Click({
    $script:autoRestart = $false
    $timer.Stop()
    $imgTimer.Stop()
    Write-Log "" "White"
    Write-Log "========================================" "Red"
    Write-Log "  HARD EXIT  //  SHUTDOWN SEQUENCE" "Red"
    Write-Log "========================================" "Red"
    Kill-VaM
    Kill-ISLC
    Invoke-RemoveSymLinks
    Write-Log "  All processes terminated." "DarkGray"
    Write-Log "  Total sessions this run: $($script:sessionCount)" "DarkGray"
    $script:activeProfile | Set-Content $PROFILE_FILE
    Write-Log "  Goodbye." "Red"
    Start-Sleep 1
    $form.Close()
})

$btnSwitch.Add_Click({
    if ($script:activeProfile -eq "VaM") {
        $script:activeProfile = "SotR"
        $btnSwitch.Text = "Switch: SotR"
        $btnSwitch.ForeColor = [System.Drawing.Color]::Orange
    } else {
        $script:activeProfile = "VaM"
        $btnSwitch.Text = "Switch: VaM"
        $btnSwitch.ForeColor = [System.Drawing.Color]::Cyan
    }
    $script:activeProfile | Set-Content $PROFILE_FILE
    Write-Log "[>] PROFILE SWAP: $($script:activeProfile) --  Hit Kill+Restart to apply." "Yellow"
})

$btnNextImg.Add_Click({
    Set-BackgroundImage
})

$btnAutoImg.Add_Click({
    $script:bgAutoRotate = !$script:bgAutoRotate
    if ($script:bgAutoRotate) {
        $btnAutoImg.Text = "Auto Img: ON"
        $btnAutoImg.ForeColor = [System.Drawing.Color]::LightGreen
        $imgTimer.Start()
    } else {
        $btnAutoImg.Text = "Auto Img: OFF"
        $btnAutoImg.ForeColor = [System.Drawing.Color]::Gray
        $imgTimer.Stop()
    }
})

$btnMono.Add_Click({
    $p = $script:profiles[$script:activeProfile]
    if (Get-Process $p.Proc -ErrorAction SilentlyContinue) {
        Write-Log "Kill VaM first before swapping mono.dll" "Red"
        return
    }
    $state = Get-MonoState
    if ($state -eq "3x Heap") {
        # -> Default
        if (!(Test-Path $MONO_DEFAULT)) { Write-Log "mono.default.dll not found in stash" "Red"; return }
        Copy-Item $MONO_DEFAULT $MONO_CURRENT -Force
        $applied = [Crc32]::Compute($MONO_CURRENT)
        if ($applied -ne $MONO_CRC_DEFAULT) { Write-Log "mono.dll CRC mismatch after apply! Got $applied" "Red"; return }
        $script:monoState = "Default"
        $btnMono.Text = "Mono: Default"
        $btnMono.ForeColor = [System.Drawing.Color]::White
        Write-Log "[>] MONO: Default (4096 heap sects) -- CRC OK [<]" "White"
    } else {
        # -> 3x Heap: extract from zip if stash missing
        if (!(Test-Path $MONO_PATCHED)) {
            if (!(Test-Path $MONO_ZIP)) { Write-Log "Mono 3x zip not found: $MONO_ZIP" "Red"; return }
            Write-Log "Extracting mono 3x patch from zip..." "Cyan"
            $zip = [System.IO.Compression.ZipFile]::OpenRead($MONO_ZIP)
            $entry = $zip.Entries | Where-Object { $_.Name -eq "mono.dll" } | Select-Object -First 1
            if (!$entry) { $zip.Dispose(); Write-Log "mono.dll not found in zip" "Red"; return }
            New-Item -ItemType Directory -Path (Split-Path $MONO_PATCHED) -Force | Out-Null
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $MONO_PATCHED, $true)
            $zip.Dispose()
            $exCRC = [Crc32]::Compute($MONO_PATCHED)
            if ($exCRC -ne $MONO_CRC_PATCHED) { Write-Log "Mono 3x CRC mismatch after extraction! Expected $MONO_CRC_PATCHED got $exCRC" "Red"; return }
            Write-Log "Mono 3x extracted and CRC verified." "Green"
        }
        Copy-Item $MONO_PATCHED $MONO_CURRENT -Force
        $applied = [Crc32]::Compute($MONO_CURRENT)
        if ($applied -ne $MONO_CRC_PATCHED) { Write-Log "mono.dll CRC mismatch after apply! Got $applied" "Red"; return }
        $script:monoState = "3x Heap"
        $btnMono.Text = "Mono: 3x Heap"
        $btnMono.ForeColor = [System.Drawing.Color]::Orange
        Write-Log "[>] MONO: 3x Heap (12288 heap sects) -- CRC OK [<]" "Orange"
    }
    Write-Log "   Hit Kill+Restart to apply." "DarkGray"
})

$btnAsm.Add_Click({
    $wasRunning = $false
    foreach ($prof in $script:profiles.Values) {
        if (Get-Process $prof.Proc -ErrorAction SilentlyContinue) { $wasRunning = $true; break }
    }
    if ($wasRunning) {
        Write-Log "[>] Killing VaM to swap ASM patch..." "Yellow"
        Kill-VaM
        Start-Sleep 2
    }
    $state = Get-AsmState
    $idx = -1
    for ($i = 0; $i -lt $script:patchCycle.Count; $i++) {
        if ($script:patchCycle[$i].Name -eq $state) { $idx = $i; break }
    }
    $ok = if ($idx -eq -1) {
        Invoke-Patch $script:patchCycle[0]
    } elseif ($idx -lt $script:patchCycle.Count - 1) {
        Invoke-Patch $script:patchCycle[$idx + 1]
    } else {
        Invoke-StockAsm
    }
    Update-AsmButton
    if ($wasRunning) { Write-Log "  VaM stopped. Start manually when ready." "DarkGray" }
})

$btnFsr.Add_Click({
    $fsrDll = "$FSR_STASH\openvr_api.dll"
    $fsrCfg = "$FSR_STASH\openvr_mod.cfg"
    if (!(Test-Path $fsrDll)) {
        Write-Log "FSR files not found in PatchStash\OpenVR_FSR" "Red"
        return
    }
    $wasRunning = $false
    foreach ($prof in $script:profiles.Values) {
        if (Get-Process $prof.Proc -ErrorAction SilentlyContinue) { $wasRunning = $true; break }
    }
    if ($wasRunning) {
        Write-Log "[>] Killing VaM to swap FSR..." "Yellow"
        Kill-VaM
        Start-Sleep 2
    }
    $state = Get-FsrState
    if ($state -eq "ON") {
        # Restore defaults
        foreach ($dir in $PLUGIN_DIRS) {
            $name = (Split-Path (Split-Path $dir) -Leaf)
            $def = "$FSR_STASH\$name\openvr_api.default.dll"
            if (Test-Path $def) {
                Copy-Item $def "$dir\openvr_api.dll" -Force
            }
            # Remove cfg
            if (Test-Path "$dir\openvr_mod.cfg") {
                Remove-Item "$dir\openvr_mod.cfg" -Force -Confirm:$false
            }
        }
        Write-Log "[>] FSR: Switched OFF (default OpenVR) [<]" "White"
    } else {
        # Install FSR
        foreach ($dir in $PLUGIN_DIRS) {
            Copy-Item $fsrDll "$dir\openvr_api.dll" -Force
            Copy-Item $fsrCfg "$dir\openvr_mod.cfg" -Force
        }
        Write-Log "[>] FSR: Switched ON (Fixed Foveated Rendering) [<]" "Lime"
    }
    Update-FsrButton
    if ($wasRunning) { Write-Log "  VaM stopped. Start manually when ready." "DarkGray" }
})


$btnBepInEx.Add_Click({
    $wasRunning = $false
    foreach ($prof in $script:profiles.Values) {
        if (Get-Process $prof.Proc -ErrorAction SilentlyContinue) { $wasRunning = $true; break }
    }
    if ($wasRunning) {
        Write-Log "[>] Killing VaM to swap BepInEx..." "Yellow"
        Kill-VaM
        Start-Sleep 2
    }
    $state = Get-BepInExState

    function Install-BepInExWinhttp($zip, $stash, $expectedCRC, $arch) {
        if (!(Test-Path $stash)) {
            if (!(Test-Path $zip)) { Write-Log "BepInEx $arch zip not found: $zip" "Red"; return $false }
            Write-Log "Extracting BepInEx $arch winhttp.dll..." "Cyan"
            New-Item -ItemType Directory -Path $BEPINEX_STASH -Force | Out-Null
            $z = [System.IO.Compression.ZipFile]::OpenRead($zip)
            $entry = $z.Entries | Where-Object { $_.FullName -eq "winhttp.dll" } | Select-Object -First 1
            if (!$entry) { $z.Dispose(); Write-Log "winhttp.dll not found in $arch zip" "Red"; return $false }
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $stash, $true)
            $z.Dispose()
            $exCRC = [Crc32]::Compute($stash)
            if ($exCRC -ne $expectedCRC) {
                Write-Log "BepInEx $arch CRC mismatch! Expected $expectedCRC got $exCRC" "Red"
                return $false
            }
            Write-Log "BepInEx $arch extracted and CRC verified." "Green"
        }
        if (Test-Path $BEPINEX_DISABLED) { Remove-Item $BEPINEX_DISABLED -Force -Confirm:$false }
        Copy-Item $stash $BEPINEX_DLL -Force
        $applied = [Crc32]::Compute($BEPINEX_DLL)
        if ($applied -ne $expectedCRC) { Write-Log "BepInEx $arch CRC mismatch after apply! Got $applied" "Red"; return $false }
        return $true
    }

    $ok = $true
    if ($state -eq "OFF" -or $state -eq "Other") {
        $ok = Install-BepInExWinhttp $BEPINEX_ZIP_X64 "$BEPINEX_STASH\winhttp.x64v23.dll" $BEPINEX_CRC_X64 "x64 v23"
        if ($ok) { Write-Log "[>] BepInEx: x64 v23 (5.4.23.2 for VaM 1.22.0.12+) -- CRC OK [<]" "Cyan" }
    } elseif ($state -eq "x64 v23") {
        $ok = Install-BepInExWinhttp $BEPINEX_ZIP_X86 "$BEPINEX_STASH\winhttp.x86v23.dll" $BEPINEX_CRC_X86 "x86 v23"
        if ($ok) { Write-Log "[>] BepInEx: x86 v23 (5.4.23.2 for VaM 1.22.0.12+) -- CRC OK [<]" "Yellow" }
    } elseif ($state -eq "x86 v23") {
        $ok = Install-BepInExWinhttp $BEPINEX_ZIP_X64_21 "$BEPINEX_STASH\winhttp.x64v21.dll" $BEPINEX_CRC_X64_21 "x64 v21"
        if ($ok) { Write-Log "[>] BepInEx: x64 v21 (5.4.21.0 for VaM 1.22.0.3) -- CRC OK [<]" "Lime" }
    } elseif ($state -eq "x64 v21") {
        $ok = Install-BepInExWinhttp $BEPINEX_ZIP_X86_21 "$BEPINEX_STASH\winhttp.x86v21.dll" $BEPINEX_CRC_X86_21 "x86 v21"
        if ($ok) { Write-Log "[>] BepInEx: x86 v21 (5.4.21.0 for VaM 1.22.0.3) -- CRC OK [<]" "Orange" }
    } else {
        # x86 v21 -> OFF
        if (Test-Path $BEPINEX_DLL) { Rename-Item $BEPINEX_DLL "winhttp.dll.disabled" -Force }
        Write-Log "[>] BepInEx: OFF (winhttp.dll disabled) [<]" "White"
    }

    Update-BepInExButton
    if ($wasRunning) {
        if ($ok) { Write-Log "  VaM stopped. Start manually when ready." "DarkGray" }
        else     { Write-Log "  BepInEx swap failed." "Red" }
    }
})

$btnQvaro.Add_Click({
    $state = Get-QvaroState
    if ($state -eq "ON") {
        Get-Process -Name $QVARO_NAME -ErrorAction SilentlyContinue | Stop-Process -Force
        Write-Log "[>] Qvaro: STOPPED [<]" "Gray"
    } else {
        if (Test-Path $QVARO_EXE) {
            Start-Process -FilePath $QVARO_EXE
            Write-Log "[>] Qvaro: STARTED [<]" "Lime"
        } else {
            Write-Log "Qvaro not found: $QVARO_EXE" "Red"
        }
    }
    Start-Sleep -Milliseconds 500
    Update-QvaroButton
})

$btnRandomMod.Add_Click({
    Invoke-RandomToggle "scenes.txt" $RANDMOD_STATE "Mod" $btnRandomMod $MODEL_STATE
})

$btnModel.Add_Click({
    Invoke-RandomToggle "models.txt" $MODEL_STATE "Model" $btnModel $RANDMOD_STATE
})

# =================================================
# IMAGE AUTO-ROTATE TIMER (30 seconds)
# =================================================
$imgTimer = New-Object System.Windows.Forms.Timer
$imgTimer.Interval = 30000
$imgTimer.Add_Tick({
    if ($script:bgAutoRotate) { Set-BackgroundImage }
})
$imgTimer.Start()

# =================================================
# BOOT SEQUENCE
# =================================================
function Show-BootSequence {
    Write-Log "========================================" "DarkCyan"
    Write-Log "  NEURAL CORE v3.0 Steam  //  BOOT SEQUENCE" "Cyan"
    Write-Log "========================================" "DarkCyan"
    Write-Log "" "White"

    # System info
    $os = (Get-CimInstance Win32_OperatingSystem)
    $cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1)
    $totalRAM = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
    $freeRAM  = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
    $drive = Get-PSDrive ($ROOT.TrimEnd(':')) -ErrorAction SilentlyContinue
    $driveUsed = if ($drive) { [math]::Round($drive.Used / 1GB) } else { "?" }
    $driveFree = if ($drive) { [math]::Round($drive.Free / 1GB) } else { "?" }

    Write-Log "  SYS   $($os.Caption)" "DarkGray"
    Write-Log "  CPU   $($cpu.Name.Trim())" "DarkGray"
    Write-Log "  RAM   ${freeRAM}GB free / ${totalRAM}GB total" "DarkGray"
    Write-Log "  DISK  ${ROOT} ${driveFree}GB free / $([math]::Round(($driveUsed+$driveFree)))GB total" "DarkGray"
    Write-Log "" "White"

    # Subsystem checks
    $dxgiState = if (Test-Path $ROOT_DXGI) { "PRESENT" } elseif (Test-Path $DXGI_DISABLED) { "DISABLED" } else { "MISSING" }
    $islcState = if (Get-Process "Intelligent standby list cleaner ISLC" -ErrorAction SilentlyContinue) { "RUNNING" } else { "STOPPED" }
    $ramDisk   = if (Test-Path "Z:\") { "MOUNTED" } else { "OFFLINE" }
    $bgCount   = $script:bgImages.Count
    $varCount  = (Get-ChildItem "$VAM_DIR\AddonPackages" -Recurse -Filter "*.var" -ErrorAction SilentlyContinue | Measure-Object).Count

    Write-Log "  SUBSYSTEM STATUS:" "Yellow"
    $monoStr = Get-MonoState

    Write-Log "    DXGI      : $dxgiState" $(if ($dxgiState -eq "PRESENT") {"Green"} else {"DarkGray"})
    Write-Log "    ISLC      : $islcState" $(if ($islcState -eq "RUNNING") {"Green"} else {"DarkGray"})
    Write-Log "    RAM Disk  : $ramDisk" $(if ($ramDisk -eq "MOUNTED") {"Green"} else {"DarkGray"})
    $asmStr = Get-AsmState

    Write-Log "    Mono      : $monoStr" $(if ($monoStr -eq "3x Heap") {"Orange"} else {"White"})
    Write-Log "    ASM Patch : $asmStr" (Get-AsmColor $asmStr)
    $fsrStr = Get-FsrState
    Write-Log "    OpenVR FSR: $fsrStr" $(if ($fsrStr -eq "ON") {"Lime"} elseif ($fsrStr -eq "N/A") {"DarkGray"} else {"White"})
    $bepStr = Get-BepInExState
    Write-Log "    BepInEx   : $bepStr" $(if ($bepStr -eq "x64 v23") {"Cyan"} elseif ($bepStr -eq "x86 v23") {"Yellow"} elseif ($bepStr -eq "x64 v21") {"Lime"} elseif ($bepStr -eq "x86 v21") {"Orange"} elseif ($bepStr -eq "Other") {"Red"} else {"White"})
    Write-Log "    Wallpapers: $bgCount loaded" "DarkGray"
    Write-Log "    Packages  : $varCount .var files" "DarkGray"
    Write-Log "" "White"

    # Profile info
    Write-Log "  PROFILES:" "Yellow"
    foreach ($name in @("VaM","SotR")) {
        $p = $script:profiles[$name]
        $exists = if (Test-Path $p.Exe) { "OK" } else { "MISSING" }
        $mark = if ($name -eq $script:activeProfile) { " [<]" } else { "" }
        Write-Log "    $name : $exists$mark" $(if ($exists -eq "OK") {"Green"} else {"Red"})
    }
    Write-Log "" "White"
    Write-Log "========================================" "DarkCyan"
    Write-Log "  INITIALIZING SUBSYSTEMS..." "Cyan"
    Write-Log "========================================" "DarkCyan"
}

Show-BootSequence

# =================================================
# SYMLINKS
# =================================================
$SYMLINK_CREATE = "$VAM_DIR\Saves\PluginData\JayJayWon\BrowserAssist\CreateBASymLinks_auto.bat"
$SYMLINK_REMOVE = "$VAM_DIR\Saves\PluginData\JayJayWon\BrowserAssist\RemoveBASymLinks_auto.bat"

function Invoke-CreateSymLinks {
    if (Test-Path $SYMLINK_CREATE) {
        Write-Log "Creating BrowserAssist SymLinks..." "Cyan"
        $p = Start-Process "cmd.exe" -ArgumentList "/c `"$SYMLINK_CREATE`"" -Wait -PassThru -WindowStyle Hidden
        Write-Log "SymLinks created (exit $($p.ExitCode))." "Green"
    }
}

function Invoke-RemoveSymLinks {
    if (Test-Path $SYMLINK_REMOVE) {
        Write-Log "Removing BrowserAssist SymLinks..." "Cyan"
        Start-Process "cmd.exe" -ArgumentList "/c `"$SYMLINK_REMOVE`"" -Wait -WindowStyle Hidden
        Write-Log "SymLinks removed." "DarkGray"
    }
}

# =================================================
# AUTO START
# =================================================
Setup-RamDisk
Invoke-CreateSymLinks
Force-Prefs
if ($script:autoLaunch) {
    Start-VaM
    Write-Log "" "White"
    Write-Log "  ALL SYSTEMS NOMINAL  //  AUTO-RESTART ACTIVE" "Green"
} else {
    Write-Log "" "White"
    Write-Log "  STANDBY  //  Auto-launch disabled. Hit Kill+Restart to start." "Yellow"
}
Write-Log "========================================" "DarkCyan"

$form.ShowDialog()
