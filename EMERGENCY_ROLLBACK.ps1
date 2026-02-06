# Emergency Rollback Script
# Run this if the adapter cleanup breaks your deployment

$ErrorActionPreference = "Stop"

Write-Host "════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  EMERGENCY ROLLBACK - Adapter Pattern Cleanup  " -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$confirmation = Read-Host "This will discard all current changes. Continue? (yes/no)"
if ($confirmation -ne "yes") {
    Write-Host "Rollback cancelled." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "Step 1: Creating backup of current state..." -ForegroundColor Cyan
git diff > "EMERGENCY_BACKUP_$(Get-Date -Format 'yyyyMMdd_HHmmss').diff"
Write-Host "✓ Backup saved" -ForegroundColor Green

Write-Host ""
Write-Host "Step 2: Resetting to clean state..." -ForegroundColor Cyan
git reset --hard HEAD
Write-Host "✓ Git reset complete" -ForegroundColor Green

Write-Host ""
Write-Host "Step 3: Removing untracked files..." -ForegroundColor Cyan
git clean -fd
Write-Host "✓ Cleanup complete" -ForegroundColor Green

Write-Host ""
Write-Host "Step 4: Applying stash backup..." -ForegroundColor Cyan
$stashExists = git stash list | Select-String "PRE_ADAPTER_CLEANUP"
if ($stashExists) {
    git stash apply stash@{0}
    Write-Host "✓ Stash applied" -ForegroundColor Green
} else {
    Write-Host "⚠ No stash found. Using diff file..." -ForegroundColor Yellow
    if (Test-Path "PRE_ADAPTER_CLEANUP.diff") {
        git apply --reverse PRE_ADAPTER_CLEANUP.diff
        Write-Host "✓ Diff applied" -ForegroundColor Green
    } else {
        Write-Host "✗ No backup found!" -ForegroundColor Red
        Write-Host "Run: git reset --hard origin/main" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  Rollback Complete!                            " -ForegroundColor Green
Write-Host "════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Check git status: git status" -ForegroundColor White
Write-Host "2. Verify files: Get-ChildItem backend/app/adapters/" -ForegroundColor White
Write-Host "3. Test backend: cd backend; python -m pytest" -ForegroundColor White
Write-Host ""
