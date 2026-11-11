$ErrorActionPreference = "Stop"

if (-not $env:SOLAR_ACCESS_TOKEN) {
    throw "Set SOLAR_ACCESS_TOKEN to a Supabase access token before running this script."
}

$baseUrl = if ($env:SOLAR_API_URL) { $env:SOLAR_API_URL.TrimEnd("/") } else { "http://localhost:8000" }
$headers = @{ Authorization = "Bearer $env:SOLAR_ACCESS_TOKEN" }

$home = Invoke-RestMethod -Method Post -Uri "$baseUrl/homes" -Headers $headers `
    -ContentType "application/json" -Body (@{ name = "API smoke test"; city = "Lahore" } | ConvertTo-Json)
Write-Output "Created home: $($home.id)"

$appliances = @(
    @{
        type = "ac"; watts = 1200; duty_factor = 0.6; surge_factor = 2
        qty = 1; hours_per_day = 8; is_essential = $false
    },
    @{
        type = "ceiling_fan"; watts = 75; duty_factor = 1; surge_factor = 1.5
        qty = 3; hours_per_day = 12; is_essential = $true
    }
)
foreach ($appliance in $appliances) {
    Invoke-RestMethod -Method Post -Uri "$baseUrl/homes/$($home.id)/appliances" `
        -Headers $headers -ContentType "application/json" `
        -Body ($appliance | ConvertTo-Json) | Out-Null
}

$listed = Invoke-RestMethod -Method Get -Uri "$baseUrl/homes/$($home.id)/appliances" -Headers $headers
Write-Output "Appliances stored with schedules: $($listed.Count)"

$report = Invoke-RestMethod -Method Post -Uri "$baseUrl/homes/$($home.id)/size" `
    -Headers $headers -ContentType "application/json" -Body "{}"
Write-Output "Daily energy: $($report.result.daily_kwh) kWh; peak: $($report.result.peak_kw) kW"
Write-Output "Report ID: $($report.report_id)"
