# SSH Environment Check Script for Raspberry Pi
$hostName = "192.168.1.63"
$userName = "pi"
$password = "pi"

Write-Host "Connecting to Raspberry Pi at $hostName..." -ForegroundColor Cyan
Write-Host "Username: $userName" -ForegroundColor Cyan
Write-Host "=" * 60

$commands = @"
echo '=== System Info ==='
uname -a
echo ''
echo '=== Python Version ==='
python3 --version
echo ''
echo '=== Pip Version ==='
pip3 --version
echo ''
echo '=== Key Python Packages ==='
pip3 list 2>/dev/null | grep -iE 'opencv|yolo|torch|tensorflow|gpio|picamera|numpy|pandas|flask|fastapi|requests|ultralytics'
echo ''
echo '=== OpenCV Version ==='
python3 -c 'import cv2; print("OpenCV:", cv2.__version__)' 2>/dev/null || echo 'OpenCV not installed'
echo ''
echo '=== GPIO Library ==='
python3 -c 'import RPi.GPIO; print("RPi.GPIO available")' 2>/dev/null || echo 'RPi.GPIO not available'
python3 -c 'import gpiozero; print("gpiozero available")' 2>/dev/null || echo 'gpiozero not available'
echo ''
echo '=== Camera ==='
python3 -c 'from picamera2 import Picamera2; print("picamera2 available")' 2>/dev/null || echo 'picamera2 not available'
echo ''
echo '=== Disk Usage ==='
df -h /
echo ''
echo '=== Memory ==='
free -h
echo ''
"@

# Use plink or ssh with password
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "ssh"
$psi.Arguments = "-o StrictHostKeyChecking=no $userName@$hostName"
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$process = [System.Diagnostics.Process]::Start($psi)

# Wait for password prompt and send password
Start-Sleep -Seconds 2
$process.StandardInput.WriteLine($password)
Start-Sleep -Seconds 1
$process.StandardInput.WriteLine($commands)
$process.StandardInput.Close()

# Read output
$output = $process.StandardOutput.ReadToEnd()
$error = $process.StandardError.ReadToEnd()

$process.WaitForExit()

Write-Host $output
if ($error) {
    Write-Host "Errors:" -ForegroundColor Red
    Write-Host $error
}
