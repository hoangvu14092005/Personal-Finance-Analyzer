# Test API Script
$baseUrl = "http://127.0.0.1:8000"
$testEmail = "test_$(Get-Random)@example.com"
$testPassword = "test1234"

Write-Host "`n=== Testing Personal Finance Analyzer API ===" -ForegroundColor Cyan

# Test 1: Health Check
Write-Host "`n[1/8] Testing Health Check..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/health" -Method GET
    Write-Host "✓ Health Check: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "✗ Health Check Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Register
Write-Host "`n[2/8] Testing Register..." -ForegroundColor Yellow
try {
    $registerBody = @{
        email = $testEmail
        password = $testPassword
        full_name = "Test User"
        currency = "VND"
        timezone = "Asia/Ho_Chi_Minh"
        locale = "vi-VN"
    } | ConvertTo-Json

    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/auth/register" -Method POST -Body $registerBody -ContentType "application/json" -SessionVariable session
    Write-Host "✓ Register: $($response.StatusCode)" -ForegroundColor Green
    $registerData = $response.Content | ConvertFrom-Json
    Write-Host "  User ID: $($registerData.user.id), Email: $($registerData.user.email)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Register Failed: $($_.Exception.Message)" -ForegroundColor Red
    $registerData = $null
}

# Test 3: Login
Write-Host "`n[3/8] Testing Login..." -ForegroundColor Yellow
try {
    $loginBody = @{
        email = $testEmail
        password = $testPassword
    } | ConvertTo-Json

    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json" -WebSession $session
    Write-Host "✓ Login: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "✗ Login Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Get Current User
Write-Host "`n[4/8] Testing Get Current User..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/auth/me" -Method GET -WebSession $session
    Write-Host "✓ Get Current User: $($response.StatusCode)" -ForegroundColor Green
    $userData = $response.Content | ConvertFrom-Json
    Write-Host "  Email: $($userData.user.email)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Get Current User Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Get Categories
Write-Host "`n[5/8] Testing Get Categories..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/categories" -Method GET -WebSession $session
    Write-Host "✓ Get Categories: $($response.StatusCode)" -ForegroundColor Green
    $categories = ($response.Content | ConvertFrom-Json).categories
    Write-Host "  Total categories: $($categories.Count)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Get Categories Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 6: Get Transactions
Write-Host "`n[6/8] Testing Get Transactions..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/transactions?limit=10" -Method GET -WebSession $session
    Write-Host "✓ Get Transactions: $($response.StatusCode)" -ForegroundColor Green
    $transactions = ($response.Content | ConvertFrom-Json).transactions
    Write-Host "  Total transactions: $($transactions.Count)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Get Transactions Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 7: Get Dashboard
Write-Host "`n[7/8] Testing Get Dashboard..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/dashboard" -Method GET -WebSession $session
    Write-Host "✓ Get Dashboard: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "✗ Get Dashboard Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 8: Logout
Write-Host "`n[8/8] Testing Logout..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/auth/logout" -Method POST -WebSession $session
    Write-Host "✓ Logout: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "✗ Logout Failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Test Complete ===" -ForegroundColor Cyan
