# Custom Domain Setup for API (api.edgechurn.ai)

## Why This Helps
Corporate firewalls often block:
- ❌ `*.run.app` domains (Cloud Run default)
- ❌ Random numeric subdomains (812016027146)
- ❌ Unknown cloud providers

But they typically allow:
- ✅ **Your own domain** (edgechurn.ai)
- ✅ Professional-looking subdomains (api.edgechurn.ai)
- ✅ Standard SSL/TLS

## Step 1: Map Domain in Cloud Run

```powershell
# Map api.edgechurn.ai to your Cloud Run service
gcloud run domain-mappings create `
  --service ecosurvey-backend-v2 `
  --domain api.edgechurn.ai `
  --region asia-south1 `
  --project watch-mail-trial
```

**This will give you DNS records to add.**

## Step 2: Add DNS Records

You'll get output like this:
```
Please add the following DNS records:
  api.edgechurn.ai  CNAME  ghs.googlehosted.com
```

**In your DNS provider (where edgechurn.ai is registered):**

1. Go to DNS settings for edgechurn.ai
2. Add a **CNAME record**:
   - **Name**: `api`
   - **Type**: `CNAME`
   - **Value**: `ghs.googlehosted.com`
   - **TTL**: 300 (or auto)

## Step 3: Wait for SSL Certificate

Cloud Run automatically provisions a free SSL certificate. This takes 15-60 minutes.

Check status:
```powershell
gcloud run domain-mappings describe api.edgechurn.ai `
  --region asia-south1 `
  --project watch-mail-trial
```

Look for: `status: ACTIVE` and `certificateStatus: ACTIVE`

## Step 4: Update Frontend

Once the domain is active, update the frontend to use the new endpoint:

**File**: `frontend/.env` or Netlify environment variables

```bash
VITE_BACKEND_URL=https://api.edgechurn.ai
```

**Redeploy frontend** after this change.

## Step 5: Test

```powershell
# Test health endpoint
curl https://api.edgechurn.ai/health

# Should return: {"status":"healthy"}
```

## Benefits

✅ **No firewall blocks** - Your own domain is trusted
✅ **Professional appearance** - api.edgechurn.ai looks legitimate
✅ **Free SSL** - Google manages the certificate
✅ **No code changes** - Just environment variable update
✅ **Same backend** - No redeployment needed

## Troubleshooting

### DNS not propagating
```powershell
# Check DNS
nslookup api.edgechurn.ai
# Should show: CNAME to ghs.googlehosted.com
```

### Certificate pending
- Wait 15-60 minutes
- Ensure DNS is correct
- Check: `gcloud run domain-mappings describe ...`

### Still getting errors
```powershell
# Check Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision" `
  --limit 20 `
  --project watch-mail-trial
```

## Alternative: Use Firebase Hosting as Proxy

If you don't want to set up DNS, you can use Firebase Hosting (which often passes through firewalls):

```powershell
# In firebase.json
{
  "hosting": {
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "ecosurvey-backend-v2",
          "region": "asia-south1"
        }
      }
    ]
  }
}
```

Then access via: `https://YOUR-FIREBASE-PROJECT.web.app/api/...`

Firebase hosting domains (*.web.app) are generally allowed by corporate firewalls.
