# Deploy RAG Chat v2 (Advanced) to a new Cloud Run service
$PROJECT_ID = "watch-mail-trial"
$REGION = "asia-south1"
$SERVICE_NAME = "ecosurvey-backend-v2"

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Deploying RAG Chat v2 (Advanced Conversational RAG) to Cloud Run" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Project: $PROJECT_ID" -ForegroundColor Yellow
Write-Host "Region: $REGION" -ForegroundColor Yellow
Write-Host "Service: $SERVICE_NAME" -ForegroundColor Yellow
Write-Host ""
Write-Host "Features:" -ForegroundColor Green
Write-Host "  - Multi-query retrieval" -ForegroundColor White
Write-Host "  - Query expansion with conversation context" -ForegroundColor White
Write-Host "  - Reciprocal Rank Fusion (RRF)" -ForegroundColor White
Write-Host "  - Maximal Marginal Relevance (MMR)" -ForegroundColor White
Write-Host "  - Session-based deduplication" -ForegroundColor White
Write-Host "  - Topic shift detection" -ForegroundColor White
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
Write-Host ""

# Deploy from source (Cloud Build will build the image automatically)
gcloud run deploy $SERVICE_NAME `
    --source . `
    --platform managed `
    --region $REGION `
    --project $PROJECT_ID `
    --allow-unauthenticated `
    --memory 4Gi `
    --cpu 2 `
    --timeout 600 `
    --port 8080 `
    --set-env-vars=$envString `
    --min-instances 0 `
    --max-instances 10 `
    --concurrency 80

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor Green
    Write-Host "Deployment complete!" -ForegroundColor Green
    Write-Host "=" * 80 -ForegroundColor Green
    Write-Host ""
    
    $SERVICE_URL = "https://$SERVICE_NAME-812016027146.$REGION.run.app"
    Write-Host "Service URL: $SERVICE_URL" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "API Endpoints:" -ForegroundColor Yellow
    Write-Host "  Health:       $SERVICE_URL/api/rag-chat-v2/health" -ForegroundColor White
    Write-Host "  Chat (basic): $SERVICE_URL/api/rag-chat" -ForegroundColor White
    Write-Host "  Chat (v2):    $SERVICE_URL/api/rag-chat-v2" -ForegroundColor White
    Write-Host "  Docs:         $SERVICE_URL/docs" -ForegroundColor White
    Write-Host ""
    
    Write-Host "Test command:" -ForegroundColor Yellow
    Write-Host "Invoke-RestMethod -Uri '$SERVICE_URL/api/rag-chat-v2' -Method POST -ContentType 'application/json' -Body '{`"question`": `"What is GDP growth?`", `"session_id`": `"test-123`", `"top_k`": 5}'" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor Red
    Write-Host "Deployment failed!" -ForegroundColor Red
    Write-Host "=" * 80 -ForegroundColor Red
}
