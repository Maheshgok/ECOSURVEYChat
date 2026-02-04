# Deploy Backend - Works with or without Redis
# If Redis is not set up, system uses Firestore + Frontend history (still robust!)

Write-Host "`n=== ECOSURVEY BACKEND DEPLOYMENT ===" -ForegroundColor Cyan

# Check if Redis exists
Write-Host "`nChecking for Redis instance..." -ForegroundColor Yellow
$redisCheck = gcloud redis instances describe ecosurvey-sessions --region=asia-south1 --project=watch-mail-trial 2>&1

if ($LASTEXITCODE -eq 0) {
    # Redis exists - deploy with Redis support
    Write-Host "✓ Redis found! Deploying with Redis caching enabled..." -ForegroundColor Green
    
    $REDIS_HOST = gcloud redis instances describe ecosurvey-sessions `
        --region=asia-south1 `
        --format='get(host)' `
        --project=watch-mail-trial
    
    Write-Host "Redis Host: $REDIS_HOST" -ForegroundColor Cyan
    
    # Check VPC connector
    $vpcCheck = gcloud compute networks vpc-access connectors describe redis-connector --region=asia-south1 --project=watch-mail-trial 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n⚠ VPC Connector not found. Creating..." -ForegroundColor Yellow
        gcloud compute networks vpc-access connectors create redis-connector `
            --region=asia-south1 `
            --range=10.8.0.0/28 `
            --network=default `
            --project=watch-mail-trial
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "✗ VPC Connector creation failed. Deploying without Redis..." -ForegroundColor Red
            $useRedis = $false
        } else {
            $useRedis = $true
        }
    } else {
        $useRedis = $true
    }
    
    if ($useRedis) {
        # Deploy with Redis
        Write-Host "`nDeploying with Redis caching..." -ForegroundColor Green
        cd backend
        gcloud run deploy ecosurvey-backend-v2 `
            --source . `
            --region asia-south1 `
            --platform managed `
            --allow-unauthenticated `
            --timeout 600s `
            --memory 2Gi `
            --set-env-vars REDIS_HOST=$REDIS_HOST,REDIS_PORT=6379 `
            --vpc-connector projects/watch-mail-trial/locations/asia-south1/connectors/redis-connector `
            --project watch-mail-trial
    }
} else {
    # No Redis - deploy without it (still works great!)
    Write-Host "⚠ Redis not found. Deploying with Firestore + Frontend history (still robust!)" -ForegroundColor Yellow
    cd backend
    gcloud run deploy ecosurvey-backend-v2 `
        --source . `
        --region asia-south1 `
        --platform managed `
        --allow-unauthenticated `
        --timeout 600s `
        --memory 2Gi `
        --project watch-mail-trial
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ Backend deployed successfully!" -ForegroundColor Green
    Write-Host "`nNext: Deploy frontend" -ForegroundColor Cyan
    Write-Host "cd ../frontend" -ForegroundColor White
    Write-Host "git add ." -ForegroundColor White
    Write-Host "git commit -m 'Fix: Robust session handling + background saves'" -ForegroundColor White
    Write-Host "git push origin main" -ForegroundColor White
} else {
    Write-Host "`n✗ Deployment failed!" -ForegroundColor Red
}
