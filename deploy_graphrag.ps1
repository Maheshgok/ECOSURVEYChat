# Deploy GraphRAG Backend to Cloud Run
# Separate service from standard RAG

param(
    [string]$ProjectId = "watch-mail-trial",
    [string]$Region = "asia-south1",
    [string]$ServiceName = "ecosurvey-graphrag"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GraphRAG Backend Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check required environment variables
$required_vars = @(
    "PINECONE_API_KEY",
    "OPENAI_API_KEY",
    "FIREBASE_PROJECT_ID"
)

foreach ($var in $required_vars) {
    if (-not (Test-Path "env:$var")) {
        Write-Host "ERROR: Missing environment variable: $var" -ForegroundColor Red
        exit 1
    }
}

Write-Host "✓ Environment variables validated" -ForegroundColor Green

# Set gcloud project
Write-Host "Setting GCP project: $ProjectId"
gcloud config set project $ProjectId

# Build and deploy
Write-Host ""
Write-Host "Building and deploying GraphRAG backend..." -ForegroundColor Yellow

gcloud run deploy $ServiceName `
    --source . `
    --dockerfile Dockerfile.graphrag `
    --region $Region `
    --allow-unauthenticated `
    --set-env-vars "DEPLOYMENT_TARGET=gcp,PINECONE_API_KEY=$env:PINECONE_API_KEY,OPENAI_API_KEY=$env:OPENAI_API_KEY,PINECONE_INDEX_NAME=ecosurvey-facts,FIREBASE_PROJECT_ID=$env:FIREBASE_PROJECT_ID,LOG_LEVEL=INFO" `
    --max-instances 20 `
    --memory 2Gi `
    --cpu 2 `
    --timeout 300 `
    --min-instances 0

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Deployment Successful!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    
    # Get service URL
    $service_url = gcloud run services describe $ServiceName --region $Region --format "value(status.url)"
    
    Write-Host ""
    Write-Host "Service URL: $service_url" -ForegroundColor Cyan
    Write-Host "Health Check: $service_url/api/health" -ForegroundColor Cyan
    
    # Test health endpoint
    Write-Host ""
    Write-Host "Testing health endpoint..." -ForegroundColor Yellow
    $response = Invoke-RestMethod -Uri "$service_url/api/health" -Method Get
    Write-Host ($response | ConvertTo-Json) -ForegroundColor Green
    
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Create Pinecone index 'ecosurvey-facts' (dimension=3072)" -ForegroundColor White
    Write-Host "2. Run fact ingestion: python backend/scripts/ingest_facts.py <pdf_path>" -ForegroundColor White
    Write-Host "3. Set up domain mapping for research.edgechurn.ai" -ForegroundColor White
    Write-Host "4. Update frontend to use GraphRAG endpoint" -ForegroundColor White
    
} else {
    Write-Host ""
    Write-Host "Deployment failed!" -ForegroundColor Red
    exit 1
}
