param(
    [string]$Message = 'MarosimGo tekshiruvi tugadi. Hisobotni chatda ko''ring.',
    [switch]$SelfTest
)

# Task-local notification. It changes no system settings and installs no global key hook.
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$alarmPath = Join-Path $env:WINDIR 'Media\Alarm01.wav'
if ($SelfTest) {
    Write-Output ('Alarm audio available: ' + (Test-Path -LiteralPath $alarmPath))
    exit 0
}

$dialog = New-Object System.Windows.Forms.Form
$dialog.Text = 'MarosimGo - vazifa xabari'
$dialog.Width = 540
$dialog.Height = 240
$dialog.StartPosition = 'CenterScreen'
$dialog.TopMost = $true
$dialog.KeyPreview = $true
$dialog.BackColor = [System.Drawing.Color]::FromArgb(15, 23, 42)
$dialog.ForeColor = [System.Drawing.Color]::White

$label = New-Object System.Windows.Forms.Label
$label.Text = $Message + "`r`n`r`nSignalni o'chirish uchun SPACE tugmasini bosing."
$label.Font = New-Object System.Drawing.Font('Segoe UI', 12)
$label.AutoSize = $false
$label.Dock = 'Fill'
$label.Padding = New-Object System.Windows.Forms.Padding(24)
$dialog.Controls.Add($label)
$dialog.Add_KeyDown({
    if ($_.KeyCode -eq [System.Windows.Forms.Keys]::Space) {
        $_.Handled = $true
        $dialog.Close()
    }
})

$sound = $null
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 1500
$timer.Add_Tick({ [System.Media.SystemSounds]::Exclamation.Play() })
$dialog.Add_Shown({
    if (Test-Path -LiteralPath $alarmPath) {
        $script:sound = New-Object System.Media.SoundPlayer($alarmPath)
        $script:sound.PlayLooping()
    } else {
        $timer.Start()
    }
    $dialog.Activate()
})
try {
    [void]$dialog.ShowDialog()
} finally {
    $timer.Stop()
    $timer.Dispose()
    if ($sound) { $sound.Stop(); $sound.Dispose() }
    $dialog.Dispose()
}
