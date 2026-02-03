# Deploy to Cloud Run directly from source
$PROJECT_ID = "watch-mail-trial"
$REGION = "asia-south1"
$SERVICE_NAME = "ecosurvey-backend"

Write-Host "Deploying to Cloud Run from source..." -ForegroundColor Cyan
Write-Host "Project: $PROJECT_ID" -ForegroundColor Yellow
Write-Host "Region: $REGION" -ForegroundColor Yellow
Write-Host ""

# Load environment variables from .env file
$envVars = @{}
Get-Content "backend\.env" | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        # Skip comments and empty lines
        if ($key -and -not $key.StartsWith('#')) {
            $envVars[$key] = $value
        }
    }
}

# Build env var string for gcloud
$envString = ($envVars.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ','

Write-Host "Setting environment variables from .env file..." -ForegroundColor Yellow

# Deploy from source (Cloud Build will build the image automatically)
gcloud run deploy $SERVICE_NAME `
    --source . `
    --platform managed `
    --region $REGION `
    --project $PROJECT_ID `
    --allow-unauthenticated `
    --memory 2Gi `
    --cpu 2 `
    --timeout 600 `
    --port 8080 `
    --set-env-vars=$envString

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Deployment complete!" -ForegroundColor Green
    Write-Host "Service URL: https://ecosurvey-backend-812016027146.asia-south1.run.app" -ForegroundColor Cyan
} else {
    Write-Host "Deployment failed!" -ForegroundColor Red
}
