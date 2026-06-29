Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$qvaroPath = 'J:\New folder\Qvaro 1.7.0.exe'
$qvaroName = 'Qvaro 1.7.0'

$form = New-Object System.Windows.Forms.Form
$form.Text = 'Qvaro'
$form.Size = New-Object System.Drawing.Size(180, 100)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedToolWindow'
$form.TopMost = $true
$form.BackColor = [System.Drawing.Color]::FromArgb(30, 30, 30)

$btn = New-Object System.Windows.Forms.Button
$btn.Size = New-Object System.Drawing.Size(140, 40)
$btn.Location = New-Object System.Drawing.Point(18, 18)
$btn.FlatStyle = 'Flat'
$btn.FlatAppearance.BorderSize = 0
$btn.Font = New-Object System.Drawing.Font('Segoe UI', 11, [System.Drawing.FontStyle]::Bold)
$btn.Cursor = [System.Windows.Forms.Cursors]::Hand

function Update-Button {
    $running = @(Get-Process -Name $qvaroName -ErrorAction SilentlyContinue).Count -gt 0
    if ($running) {
        $btn.Text = '  ON   [stop]'
        $btn.BackColor = [System.Drawing.Color]::FromArgb(0, 160, 80)
        $btn.ForeColor = [System.Drawing.Color]::White
    } else {
        $btn.Text = '  OFF  [start]'
        $btn.BackColor = [System.Drawing.Color]::FromArgb(80, 80, 80)
        $btn.ForeColor = [System.Drawing.Color]::LightGray
    }
}

$btn.Add_Click({
    $running = @(Get-Process -Name $qvaroName -ErrorAction SilentlyContinue).Count -gt 0
    if ($running) {
        Get-Process -Name $qvaroName -ErrorAction SilentlyContinue | Stop-Process -Force
    } else {
        if (Test-Path $qvaroPath) {
            Start-Process -FilePath $qvaroPath
        } else {
            [System.Windows.Forms.MessageBox]::Show("Not found:`n$qvaroPath", 'Qvaro Toggle', 'OK', 'Warning')
        }
    }
    Start-Sleep -Milliseconds 400
    Update-Button
})

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 2000
$timer.Add_Tick({ Update-Button })
$timer.Start()

$form.Controls.Add($btn)
Update-Button
$form.ShowDialog() | Out-Null
$timer.Stop()
