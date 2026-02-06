# Post-build script to organize files for Firebase subdirectory hosting

Write-Host "Organizing build files for subdirectory deployment..." -ForegroundColor Cyan

# Create the subdirectory structure in dist
$distPath = "frontend/dist"
$subPath = "frontend/dist/chatbot/ecosurveybudget2026"

# Create directories
New-Item -Path "$subPath/assets" -ItemType Directory -Force | Out-Null

# Copy files to subdirectory (don't move, in case root also needs them)
Copy-Item -Path "$distPath/assets/*" -Destination "$subPath/assets/" -Recurse -Force
Copy-Item -Path "$distPath/index.html" -Destination "$subPath/" -Force

# Use landing.html as root index
if (Test-Path "$distPath/landing.html") {
    Copy-Item -Path "$distPath/landing.html" -Destination "$distPath/index.html" -Force
}

Write-Host "Files organized for /chatbot/ecosurveybudget2026/" -ForegroundColor Green
Write-Host "Structure:" -ForegroundColor Cyan
Write-Host "  frontend/dist/index.html (root)" -ForegroundColor Gray
Write-Host "  frontend/dist/chatbot/ecosurveybudget2026/index.html" -ForegroundColor Gray
Write-Host "  frontend/dist/chatbot/ecosurveybudget2026/assets/" -ForegroundColor Gray
