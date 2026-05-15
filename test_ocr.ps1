# Test OCR Upload
$baseUrl = "http://localhost:8000"
$testEmail = "ocr_test_$(Get-Random)@example.com"
$testPassword = "test1234"

Write-Host "`n=== Testing OCR Upload ===" -ForegroundColor Cyan

# 1. Register user
Write-Host "`n[1/4] Registering user..." -ForegroundColor Yellow
$registerBody = @{
    email = $testEmail
    password = $testPassword
    currency = "VND"
    timezone = "Asia/Ho_Chi_Minh"
    locale = "vi-VN"
} | ConvertTo-Json

try {
    $registerResponse = Invoke-WebRequest -Uri "$baseUrl/api/v1/auth/register" -Method POST -Body $registerBody -ContentType "application/json" -SessionVariable session
    Write-Host "✓ User registered: $testEmail" -ForegroundColor Green
} catch {
    Write-Host "✗ Registration failed: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# 2. Login
Write-Host "`n[2/4] Logging in..." -ForegroundColor Yellow
$loginBody = @{
    email = $testEmail
    password = $testPassword
} | ConvertTo-Json

try {
    $loginResponse = Invoke-WebRequest -Uri "$baseUrl/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json" -WebSession $session
    Write-Host "✓ Login successful" -ForegroundColor Green
} catch {
    Write-Host "✗ Login failed: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# 3. Create a test image file (1x1 pixel PNG)
Write-Host "`n[3/4] Creating test image..." -ForegroundColor Yellow
$testImagePath = "test_receipt.png"
# Base64 of a 1x1 transparent PNG
$pngBase64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
$pngBytes = [Convert]::FromBase64String($pngBase64)
[IO.File]::WriteAllBytes($testImagePath, $pngBytes)
Write-Host "✓ Test image created: $testImagePath" -ForegroundColor Green

# 4. Upload receipt
Write-Host "`n[4/4] Uploading receipt..." -ForegroundColor Yellow
try {
    $boundary = [System.Guid]::NewGuid().ToString()
    $fileContent = [IO.File]::ReadAllBytes($testImagePath)
    
    $bodyLines = @(
        "--$boundary",
        'Content-Disposition: form-data; name="file"; filename="test_receipt.png"',
        'Content-Type: image/png',
        '',
        [System.Text.Encoding]::GetEncoding('iso-8859-1').GetString($fileContent),
        "--$boundary--"
    )
    
    $body = $bodyLines -join "`r`n"
    
    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/receipts/upload" -Method POST -Body $body -ContentType "multipart/form-data; boundary=$boundary" -WebSession $session
    
    Write-Host "✓ Upload successful: $($response.StatusCode)" -ForegroundColor Green
    $data = $response.Content | ConvertFrom-Json
    Write-Host "  Receipt ID: $($data.id)" -ForegroundColor Gray
    Write-Host "  Status: $($data.status)" -ForegroundColor Gray
    
    if ($data.status -eq "QUEUED") {
        Write-Host "`n  OCR job queued. Check worker logs for processing." -ForegroundColor Cyan
    }
} catch {
    Write-Host "✗ Upload failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "  Response: $responseBody" -ForegroundColor Gray
    }
}

# Cleanup
Remove-Item $testImagePath -ErrorAction SilentlyContinue

Write-Host "`n=== Test Complete ===" -ForegroundColor Cyan
