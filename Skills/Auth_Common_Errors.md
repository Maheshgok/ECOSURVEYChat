# Common Errors: Authentication Skills (Phase 2)

---

## 🚨 CRITICAL: PII Storage Violations

### **ERROR: Email Column in Database**

**Symptom:**
```sql
\d users
-- Shows: email VARCHAR(255)
```

**This is a STOP CONDITION. Fix immediately:**

```sql
-- Drop PII columns
ALTER TABLE users DROP COLUMN IF EXISTS email;
ALTER TABLE users DROP COLUMN IF EXISTS name;
ALTER TABLE users DROP COLUMN IF EXISTS picture;
ALTER TABLE users DROP COLUMN IF EXISTS access_token;
ALTER TABLE users DROP COLUMN IF EXISTS refresh_token;
```

**Prevention:**
- Never access `user_info['email']` in code
- Only use `user_info['sub']` for pseudo ID generation

---

## Error 1: Invalid Client Error

**Symptom:**
```
AuthlibHTTPError: invalid_client
```

**Causes:**
1. Wrong `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET`
2. Credentials not for a Web application
3. Redirect URI mismatch

**Solutions:**

**Check credentials:**
```bash
# Verify env vars are loaded
docker-compose exec api python -c "from app.core.config import settings; print(settings.GOOGLE_CLIENT_ID)"
```

**Check redirect URI in Google Console:**
- Must exactly match `http://localhost:8000/auth/callback` (including port)
- No trailing slashes
- Check both Authorized JavaScript origins AND Authorized redirect URIs

**Check OAuth client type:**
- Must be "Web application" not "Desktop app" or "Mobile app"

---

## Error 2: Redirect URI Mismatch

**Symptom:**
```
Error 400: redirect_uri_mismatch
The redirect URI in the request does not match
```

**Solution:**
```python
# In auth.py, ensure redirect_uri uses correct scheme
@router.get("/callback")
async def auth_callback(request: Request, ...):
    # Authlib auto-detects, but if behind proxy:
    redirect_uri = str(request.url_for('auth_callback'))
    # May need to force https if behind proxy
    if settings.FORCE_HTTPS:
        redirect_uri = redirect_uri.replace('http://', 'https://')
```

**Google Console:**
Add all possible redirect URIs:
- `http://localhost:8000/auth/callback`
- `https://api.yourdomain.com/auth/callback`

---

## Error 3: Session Cookie Not Set

**Symptom:**
User logs in successfully but `/api/me` returns 401

**Cause:** Cookie not set or not sent

**Debug:**
```python
# In auth callback, log cookie setting
response.set_cookie(...)
print(f"Set cookie: {session_token[:20]}...")
```

**Browser check:**
- Open DevTools → Application → Cookies
- Look for `session` cookie
- Check `HttpOnly`, `Secure`, `SameSite` flags

**Common issues:**
1. `Secure=True` but using HTTP → Remove Secure flag for local dev
2. `SameSite=Strict` blocking cross-site → Use `Lax`
3. Domain mismatch → Don't set domain for localhost

**Fix for local development:**
```python
response.set_cookie(
    key="session",
    value=session_token,
    httponly=True,
    secure=False,  # False for local HTTP
    samesite="lax",
    max_age=7 * 24 * 60 * 60
)
```

---

## Error 4: JWT Decode Error

**Symptom:**
```
jose.exceptions.JWTError: Unable to verify token
```

**Cause:** Using `python-jose` instead of `authlib`

**Solution:**
Don't manually decode Google ID tokens. Let Authlib handle it:

```python
# WRONG:
from jose import jwt
claims = jwt.decode(token, ...)

# RIGHT:
token = await oauth.google.authorize_access_token(request)
user_info = token.get('userinfo')  # Authlib validates automatically
```

---

## Error 5: Pseudo ID Collision

**Symptom:**
Different Google users get the same `user_pseudo_id`

**Cause:** `SERVER_SALT` not set or empty

**Solution:**
```python
# Generate strong salt
import secrets
print(secrets.token_urlsafe(32))  # Use this as SERVER_SALT
```

**Update `.env`:**
```
SERVER_SALT=<generated-random-string>
```

**Verify:**
```python
from app.services.auth_service import generate_pseudo_id
id1 = generate_pseudo_id("google_sub_123")
id2 = generate_pseudo_id("google_sub_456")
assert id1 != id2  # Must be different
```

---

## Error 6: Session Expiry Not Working

**Symptom:**
Old sessions remain valid indefinitely

**Cause:** `max_age` not set properly in serializer

**Solution:**
```python
# In sessions.py
class SessionManager:
    def __init__(self):
        self.max_age = 7 * 24 * 60 * 60  # 7 days in seconds
    
    def validate_session(self, token: str) -> Optional[str]:
        try:
            data = self.serializer.loads(
                token, 
                max_age=self.max_age  # MUST pass max_age
            )
            return data.get('user_pseudo_id')
        except (BadSignature, SignatureExpired):
            return None
```

---

## Error 7: CORS Blocks OAuth Callback

**Symptom:**
```
CORS policy: No 'Access-Control-Allow-Origin' header
```

**Cause:** OAuth callback is NOT subject to CORS (it's a server redirect)

**If you see this:**
- You're making AJAX requests to `/auth/login` → Don't
- Use `<a href="/auth/login">` or `window.location.href = "/auth/login"`

**CORS is needed for:**
- `/api/chat` (POST)
- `/api/chat/stream` (SSE)
- `/api/corpus/briefing` (GET)

**CORS is NOT needed for:**
- `/auth/login` (full page redirect)
- `/auth/callback` (full page redirect)

---

## Error 8: State Parameter Mismatch

**Symptom:**
```
AuthlibHTTPError: mismatching_state
```

**Cause:** Session state lost between `/auth/login` and `/auth/callback`

**Solution:**
Authlib stores state in session. Ensure:
1. Session middleware enabled
2. Session secret configured
3. Cookies working

**For Starlette/FastAPI:**
```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SESSION_SECRET
)
```

---

## Error 9: User Not Created in Database

**Symptom:**
Login succeeds but `get_current_user` fails with 404

**Cause:** Database transaction not committed

**Solution:**
```python
def get_or_create_user(db: Session, google_sub: str) -> User:
    pseudo_id = generate_pseudo_id(google_sub)
    user = db.query(User).filter(User.user_pseudo_id == pseudo_id).first()
    
    if not user:
        user = User(user_pseudo_id=pseudo_id)
        db.add(user)
        db.commit()  # MUST commit
        db.refresh(user)  # MUST refresh
    
    return user
```

---

## Error 10: Logout Doesn't Clear Cookie

**Symptom:**
After logout, user still authenticated

**Cause:** Cookie delete parameters must match set parameters

**Solution:**
```python
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="session",
        # Must match the path/domain used in set_cookie
        path="/",
        domain=None  # or match your domain
    )
    return {"message": "Logged out"}
```

---

## Error 11: authlib Import Errors

**Symptom:**
```
ImportError: cannot import name 'OAuth' from 'authlib.integrations.starlette_client'
```

**Cause:** Missing starlette integration

**Solution:**
```bash
pip install authlib[starlette]
```

Or in `requirements.txt`:
```
authlib==1.2.1
starlette==0.27.0
```

---

## Error 12: Development vs Production Config

**Symptom:**
- Works locally but fails in production
- Or: Works in production but fails locally

**Cause:** Different cookie/redirect settings needed

**Solution:**
```python
# In config.py
class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    IS_PRODUCTION: bool = False
    
    @property
    def cookie_secure(self) -> bool:
        return self.IS_PRODUCTION
    
    @property
    def redirect_scheme(self) -> str:
        return "https" if self.IS_PRODUCTION else "http"
```

```python
# In auth.py
response.set_cookie(
    key="session",
    value=session_token,
    httponly=True,
    secure=settings.cookie_secure,  # True in prod, False in dev
    samesite="lax",
    max_age=7 * 24 * 60 * 60
)
```

---

## 🔍 Debugging Checklist

When Phase 2 tests fail:

1. **Verify OAuth credentials:**
   ```bash
   echo $GOOGLE_CLIENT_ID
   echo $GOOGLE_CLIENT_SECRET
   ```

2. **Check database:**
   ```sql
   SELECT * FROM users;
   -- Verify only pseudo_id stored, no email/name
   ```

3. **Test pseudo ID generation:**
   ```python
   from app.services.auth_service import generate_pseudo_id
   print(generate_pseudo_id("test_sub_123"))
   # Should be 64-char hex string
   ```

4. **Check session creation:**
   ```python
   from app.core.sessions import session_manager
   token = session_manager.create_session("test_pseudo_id")
   print(token)
   # Should be base64 string
   
   pseudo_id = session_manager.validate_session(token)
   print(pseudo_id)  # Should be "test_pseudo_id"
   ```

5. **Browser cookie check:**
   - DevTools → Application → Cookies
   - Look for `session` cookie
   - Verify flags: HttpOnly=Yes, Secure=(if HTTPS), SameSite=Lax

---

## ⚠️ Stop Condition Enforcement

**Before proceeding to Phase 3:**

Run this query:
```sql
\d users
```

**MUST NOT contain:**
- `email`
- `name`
- `picture`
- `given_name`
- `family_name`
- `locale`
- `access_token`
- `refresh_token`
- `id_token`

**MUST contain ONLY:**
- `id`
- `user_pseudo_id`
- `created_at`
- `last_login`

**If any PII columns exist → STOP and delete them.**

---

## 📞 When to Escalate

Escalate if:
- Google OAuth setup fails after following docs exactly
- Pseudo ID collisions occur despite proper salt
- Session management breaks across multiple FastAPI workers
- Cookie security requirements conflict with deployment environment
