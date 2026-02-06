# Firebase Hosting Deployment Script
# Run this whenever you want to deploy frontend changes

Write-Host "🔨 Building frontend..." -ForegroundColor Cyan
cd frontend
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

cd ..

Write-Host "🚀 Deploying to Firebase Hosting..." -ForegroundColor Cyan
firebase deploy --only hosting

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Deployment complete!" -ForegroundColor Green
    Write-Host "🌐 Live at: https://edgechurn.ai" -ForegroundColor Green
    Write-Host "🌐 Backup: https://watch-mail-trial.web.app" -ForegroundColor Gray
} else {
    Write-Host "❌ Deployment failed!" -ForegroundColor Red
    exit 1
}
