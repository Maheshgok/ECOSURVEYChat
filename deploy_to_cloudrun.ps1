# Deploy to Google Cloud Run
# Prerequisites: gcloud CLI installed and authenticated

$PROJECT_ID = "watch-mail-trial"
$REGION = "asia-south1"
$SERVICE_NAME = "ecosurvey-backend"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

Write-Host "🚀 Deploying to Cloud Run..." -ForegroundColor Cyan
Write-Host "Project: $PROJECT_ID" -ForegroundColor Yellow
Write-Host "Region: $REGION" -ForegroundColor Yellow
Write-Host "Service: $SERVICE_NAME" -ForegroundColor Yellow
Write-Host ""

# Step 1: Build the Docker image
Write-Host "📦 Step 1: Building Docker image..." -ForegroundColor Green
docker build -t $IMAGE_NAME .
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker build failed!" -ForegroundColor Red
    exit 1
}

# Step 2: Push to Google Container Registry
Write-Host "☁️  Step 2: Pushing image to GCR..." -ForegroundColor Green
docker push $IMAGE_NAME
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker push failed!" -ForegroundColor Red
    exit 1
}

# Step 3: Deploy to Cloud Run
Write-Host "🚀 Step 3: Deploying to Cloud Run..." -ForegroundColor Green
gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_NAME `
    --platform managed `
    --region $REGION `
    --project $PROJECT_ID `
    --allow-unauthenticated `
    --memory 2Gi `
    --cpu 2 `
    --timeout 300 `
    --set-env-vars "DEBUG=False,ENVIRONMENT=production" `
    --port 8080

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Cloud Run deployment failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "🔗 Service URL: https://ecosurvey-backend-812016027146.asia-south1.run.app" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 View logs:" -ForegroundColor Yellow
Write-Host "  gcloud run services logs read $SERVICE_NAME --region $REGION --project $PROJECT_ID" -ForegroundColor Gray
