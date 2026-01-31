# Common Errors & Solutions

**Last Updated:** January 31, 2026  
**Purpose:** Help avoid recurring errors in Phase 1 and beyond  
**Status:** Living document - update as new errors are discovered

---

## Table of Contents

1. [Syntax Errors](#syntax-errors)
2. [Python Environment Errors](#python-environment-errors)
3. [Database Errors](#database-errors)
4. [FastAPI/Backend Errors](#fastapiberend-errors)
5. [Configuration Errors](#configuration-errors)
6. [Dependency Version Errors](#dependency-version-errors)
7. [Windows-Specific Errors](#windows-specific-errors)
8. [Prevention Checklist](#prevention-checklist)

---

## Syntax Errors

### 1. Missing Colons in Python

**Error Message:**
```
SyntaxError: invalid syntax
  File "app/models.py", line 42
    def get_data(self) # missing colon
                      ^
```

**Cause:** Missing `:` after function/class/if/for definitions

**Solution:**
```python
# ❌ Wrong
def get_data(self)
    return self.data

# ✅ Correct
def get_data(self):
    return self.data
```

**Prevention:** Use IDE syntax checking (Pylint, Pylance)

---

### 2. Indentation Errors

**Error Message:**
```
IndentationError: expected an indented block
  File "app/core/database.py", line 18
    def init_db():
        pass  # All code following must be indented
    invalid_line()  # Not indented enough
```

**Cause:** Inconsistent indentation (mix of tabs and spaces)

**Solution:**
```python
# ❌ Wrong (mixed tabs/spaces)
def init_db():
    engine = create_engine(DATABASE_URL)
        # Extra indentation

# ✅ Correct (consistent 4 spaces)
def init_db():
    engine = create_engine(DATABASE_URL)
    return engine
```

**Prevention:** 
- Use VS Code setting: `"editor.insertSpaces": true`
- Set tab size: `"editor.tabSize": 4`
- Run formatter: `black app/` before committing

---

### 3. String Quote Mismatch

**Error Message:**
```
SyntaxError: EOL while scanning string literal
  File "app/api/health.py", line 5
    message = "Health check failed'
                                  ^
```

**Cause:** Opening and closing quotes don't match

**Solution:**
```python
# ❌ Wrong
message = "Health check failed'

# ✅ Correct
message = "Health check failed"
# or
message = 'Health check failed'
```

**Prevention:** Use IDE bracket matching (built into VS Code)

---

### 4. Missing Import Statements

**Error Message:**
```
NameError: name 'FastAPI' is not defined
  File "app/main.py", line 1
    app = FastAPI()
          ^
```

**Cause:** Missing `from fastapi import FastAPI`

**Solution:**
```python
# ❌ Wrong - no import
app = FastAPI()

# ✅ Correct - with import
from fastapi import FastAPI

app = FastAPI()
```

**Prevention:** 
- Check imports at top of file
- Use VS Code "Organize Imports" feature
- Run: `python -c "from app.main import app"` to test

---

### 5. Function Definition Inside Function

**Error Message:**
```
IndentationError: unexpected indent
  File "app/models.py", line 25
    def nested_function():
        ^^^^^^
```

**Cause:** Accidentally indenting a function definition

**Solution:**
```python
# ❌ Wrong
class User:
    def get_user(self):
        def nested():  # Don't define functions inside methods unless intended
            pass
        return self.id

# ✅ Correct
class User:
    def get_user(self):
        return self.id

    def nested(self):  # Define at class level
        pass
```

---

## Python Environment Errors

### 1. ModuleNotFoundError with Virtual Environment

**Error Message:**
```
ModuleNotFoundError: No module named 'fastapi'
  File "app/main.py", line 1
    from fastapi import FastAPI
```

**Cause:** Virtual environment not activated or dependency not installed

**Solution:**
```powershell
# Check if .venv is activated (should show (.venv) in prompt)
.\.venv\Scripts\Activate.ps1

# If error: "cannot be loaded because running scripts is disabled"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Reinstall dependencies
pip install -r backend\requirements.txt

# Verify FastAPI is installed
pip list | findstr fastapi
```

**Prevention:**
- Always activate venv first: `.\.venv\Scripts\Activate.ps1`
- Check Python executable: `which python` or `Get-Command python`
- Test imports before running app: `python -c "import fastapi; print('OK')"`

---

### 2. Wrong Python Version

**Error Message:**
```
SyntaxError: Match statements require Python 3.10+
  File "app/api/chat.py", line 50
    match response_type:
          ^
```

**Cause:** Using Python 3.9 or older syntax from 3.10+

**Solution:**
```powershell
# Check current Python version
python --version
# Output should be: Python 3.10.11 or higher

# If wrong version, specify full path
C:\Python310\python.exe --version

# Update .venv if needed
python -m venv .venv --upgrade
```

**Prevention:**
- Use Python 3.10+ (project requirement)
- Document Python version in README
- Add version check to app startup

---

### 3. pip Install Failures

**Error Message:**
```
ERROR: Could not find a version that satisfies the requirement openpyxl==3.11.0
```

**Cause:** Invalid package version (openpyxl max version is 3.1.5)

**Solution:**
```powershell
# Check available versions
pip index versions openpyxl

# Update requirements.txt with valid version
# openpyxl==3.11.0 → openpyxl==3.1.5

# Clear pip cache and reinstall
pip cache purge
pip install -r backend\requirements.txt
```

**Prevention:**
- Always check PyPI before specifying versions
- Test `pip install` locally before committing
- Use `pip list` to verify installed versions

---

### 4. Circular Import Errors

**Error Message:**
```
ImportError: cannot import name 'Base' from partially initialized module 'app.core.database'
```

**Cause:** File A imports from B, and B imports from A

**Solution:**
```python
# ❌ Wrong - circular
# app/core/database.py
from app.models import Base

# app/models/__init__.py
from app.core.database import engine

# ✅ Correct - import at usage point
# app/models/__init__.py
# Move import inside function
def init_models():
    from app.core.database import engine
    return engine
```

**Prevention:**
- Use type hints with `TYPE_CHECKING`:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.core.database import Engine
```

---

## Database Errors

### 1. PostgreSQL Connection Refused

**Error Message:**
```
psycopg2.OperationalError: could not connect to server: 
Connection refused - Is the server running on host "localhost" (127.0.0.1) port 5432?
```

**Cause:** PostgreSQL service not running

**Solution (Windows):**
```powershell
# Check if PostgreSQL is running
Get-Service -Name "postgresql*"

# Start service if stopped
Start-Service -Name "postgresql-x64-15"

# Or use pgAdmin to start

# Verify connection
psql -U postgres -h localhost -c "SELECT 1"
```

**Prevention:**
- Start PostgreSQL before running app
- Add startup script: `backend/start_dev.ps1`
```powershell
# start_dev.ps1
Start-Service -Name "postgresql-x64-15"
.\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app.main:app --reload
```

---

### 2. Database Does Not Exist

**Error Message:**
```
psycopg2.ProgrammingError: FATAL: database "survey_chat" does not exist
```

**Cause:** Database not created yet

**Solution:**
```powershell
# Create database
psql -U postgres -c "CREATE DATABASE survey_chat;"

# Verify creation
psql -U postgres -d survey_chat -c "\dt"
```

**Prevention:**
- Run `python init_phase1.py` after creating database
- Check database exists: `psql -U postgres -c "\l" | findstr survey_chat`

---

### 3. Table Does Not Exist

**Error Message:**
```
psycopg2.ProgrammingError: relation "corpus" does not exist
```

**Cause:** Database created but tables not initialized

**Solution:**
```powershell
# Run migrations
psql -U postgres -d survey_chat -f backend\migrations\001_init_phase1.sql

# Or use Python script
cd backend
python init_phase1.py

# Verify tables created
psql -U postgres -d survey_chat -c "\dt"
```

---

### 4. Authentication Failed

**Error Message:**
```
FATAL: password authentication failed for user "postgres"
```

**Cause:** Wrong password in .env or connection string

**Solution:**
```powershell
# Test connection with correct password
psql -U postgres -h localhost -d survey_chat

# If you forgot password, reset it
psql -U postgres
postgres=# ALTER USER postgres WITH PASSWORD 'new_password';

# Update .env
DB_PASSWORD=new_password
```

**Prevention:**
- Note PostgreSQL password during installation
- Don't share .env file (add to .gitignore)
- Use strong passwords in production only

---

### 5. Port Already in Use

**Error Message:**
```
ERROR: could not bind socket: Only one usage of each socket address
Address already in use
```

**Cause:** Port 5432 (PostgreSQL) or 8000 (FastAPI) already in use

**Solution:**
```powershell
# Find what's using port 5432
Get-NetTCPConnection -LocalPort 5432 | Select-Object ProcessName, OwningProcess

# Kill the process
Stop-Process -Id <PID> -Force

# Or use different port
# For PostgreSQL: Stop current service, edit postgresql.conf

# For FastAPI: 
python -m uvicorn app.main:app --port 8001

# Update .env or code if changing ports
```

---

## FastAPI/Backend Errors

### 1. Startup Hook Fails Silently

**Error Message:**
```
ERROR: Startup event "startup" raised an exception
ModuleNotFoundError: No module named 'app.models'
```

**Cause:** Models not found during app startup

**Solution:**
```python
# app/main.py
@app.on_event("startup")
async def startup_event():
    try:
        # Initialize models
        from app.models import Base  # Explicit import
        logger.info("Models loaded")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        # Don't crash app if optional initialization fails
```

**Prevention:**
- Always wrap startup hooks in try-except
- Test imports separately: `python -c "from app.models import *"`
- Check logs for startup errors

---

### 2. CORS Errors

**Error Message:**
```
Access to XMLHttpRequest from origin blocked by CORS policy
```

**Cause:** Frontend calling backend without proper CORS headers

**Solution:**
```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Prevention:**
- Add CORS middleware early in app setup
- Restrict origins in production (not "*")
- Test with browser DevTools > Network tab

---

### 3. Response Validation Error

**Error Message:**
```
response = await superuser_token_generator(db=db)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: unsupported operand type(s) for +: 'coroutine' and 'str'
```

**Cause:** Using async function without await

**Solution:**
```python
# ❌ Wrong
response = get_token()  # coroutine returned, not result

# ✅ Correct
response = await get_token()  # waits for result

# ✅ Also correct for sync
response = get_token_sync()  # calls sync version
```

**Prevention:**
- Use IDE async/await checking
- Mark functions properly: `async def` or `def`
- Use type hints to catch mismatches

---

### 4. Pydantic Validation Error

**Error Message:**
```
pydantic_core._pydantic_core.PydanticCustomError: 2 validation errors
value_error.missing (type=value_error.missing)
```

**Cause:** Missing required field in request body

**Solution:**
```python
# ❌ Wrong - missing 'name'
request = {"email": "user@example.com"}

# ✅ Correct - all required fields
request = {"email": "user@example.com", "name": "John"}

# Or make field optional
class User(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
```

**Prevention:**
- Check endpoint schema: http://localhost:8000/docs
- Use type hints properly
- Test with curl or Postman

---

## Configuration Errors

### 1. Missing .env File

**Error Message:**
```
FileNotFoundError: .env file not found
```

**Cause:** .env file missing from project root

**Solution:**
```powershell
# Create .env from template
Copy-Item "backend\.env.example" ".env"

# Or create manually
@"
DB_HOST=localhost
DB_PORT=5432
DB_NAME=survey_chat
DB_USER=postgres
DB_PASSWORD=postgres
ENVIRONMENT=development
DEBUG=true
"@ | Set-Content ".env"
```

**Prevention:**
- Commit .env.example (template) to git
- Document .env format in README
- Check for .env in .gitignore (don't commit sensitive data)

---

### 2. Invalid Environment Variable

**Error Message:**
```
ValueError: GOOGLE_CLIENT_ID must be set
```

**Cause:** Required env var not in .env or not loaded

**Solution:**
```python
# app/core/settings.py

# ❌ Wrong - crashes if missing
GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID")

# ✅ Correct - optional for Phase 1
GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")

# ✅ Also correct - with default
GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "dev-default-id")
```

**Prevention:**
- Use Pydantic settings for validation
- Mark Phase 1 fields as Optional
- Provide sensible defaults for dev environment

---

### 3. Relative Path Issues

**Error Message:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'backend/migrations/001_init_phase1.sql'
```

**Cause:** Running from wrong directory (not project root)

**Solution:**
```powershell
# ❌ Wrong working directory
cd backend
python -m uvicorn app.main:app  # Will fail to find migrations

# ✅ Correct - from project root
cd C:\Users\...\ECOSURVEYCHat
python -m uvicorn backend.app.main:app

# ✅ Or change directory explicitly
cd backend
python -m uvicorn app.main:app --reload
```

**Prevention:**
- Use absolute paths in code: `Path(__file__).parent`
- Create startup scripts that cd to correct directory
- Document expected working directory in README

---

## Dependency Version Errors

### 1. Incompatible SQLAlchemy Version

**Error Message:**
```
ImportError: cannot import name 'declarative_base' from 'sqlalchemy'
```

**Cause:** Using SQLAlchemy 2.0+ syntax with 1.x API

**Solution:**
```python
# ❌ Wrong for SQLAlchemy 2.0+
from sqlalchemy.ext.declarative import declarative_base

# ✅ Correct for SQLAlchemy 2.0+
from sqlalchemy.orm import declarative_base
```

**Update requirements.txt:**
```
sqlalchemy==2.0.23  # Use 2.0+
```

**Prevention:**
- Check requirements.txt versions before pip install
- Test imports after updating dependencies
- Review changelog for breaking changes

---

### 2. Pydantic V1 vs V2

**Error Message:**
```
ImportError: cannot import name 'BaseSettings' from 'pydantic'
```

**Cause:** Using Pydantic V1 code with V2

**Solution:**
```python
# ❌ Wrong for Pydantic 2
from pydantic import BaseSettings

# ✅ Correct for Pydantic 2
from pydantic_settings import BaseSettings
```

**Update requirements.txt:**
```
pydantic==2.5.0
pydantic-settings==2.1.0
```

**Prevention:**
- Document Pydantic version (2.x for this project)
- Install pydantic-settings separately
- Use type hints from pydantic (V2 style)

---

### 3. psycopg2 Binary vs Source

**Error Message:**
```
error: Microsoft Visual C++ 14.0 or greater is required
```

**Cause:** Installing psycopg2 (source) instead of psycopg2-binary

**Solution:**
```powershell
# Use binary version (no compilation needed)
pip uninstall psycopg2
pip install psycopg2-binary

# Update requirements.txt
psycopg2-binary==2.9.9  # Not psycopg2
```

**Prevention:**
- Always use psycopg2-binary on Windows
- Document in requirements.txt
- Test `pip install` on fresh environment

---

## Windows-Specific Errors

### 1. PowerShell Execution Policy

**Error Message:**
```
.venv\Scripts\Activate.ps1 cannot be loaded because running scripts is disabled
```

**Cause:** Windows PowerShell execution policy too restrictive

**Solution:**
```powershell
# Check current policy
Get-ExecutionPolicy

# Set to allow local scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Now activate venv
.\.venv\Scripts\Activate.ps1
```

**Prevention:**
- Document this in PHASE_1_QUICK_START.md
- Create .bat file as alternative (doesn't need execution policy)

```batch
@echo off
REM start_dev.bat
call .venv\Scripts\activate.bat
cd backend
python -m uvicorn app.main:app --reload
```

---

### 2. Path Separator Confusion

**Error Message:**
```
python.exe: can't open file 'backend/requirements.txt': [Errno 2]
```

**Cause:** Using Unix forward slashes in Windows paths

**Solution:**
```powershell
# ❌ Wrong on Windows
pip install -r backend/requirements.txt

# ✅ Correct on Windows
pip install -r backend\requirements.txt

# ✅ Also works with forward slashes in Python code
Path("backend/requirements.txt")  # Python handles both
```

**Prevention:**
- Use backslashes in PowerShell commands
- Use forward slashes in Python code (os.path handles conversion)
- Use pathlib.Path for cross-platform code

---

### 3. Line Ending Issues (CRLF vs LF)

**Error Message:**
```
SyntaxError: invalid syntax
  File "app/main.py", line 1
    #!/usr/bin/env python
    ^
```

**Cause:** Mixing CRLF (Windows) and LF (Unix) line endings

**Solution:**
```powershell
# VS Code: Set end of line to LF (bottom right of editor)
# Or in .editorconfig:
[*]
end_of_line = lf

# Git: Configure for your platform
git config --global core.autocrlf true  # Windows
git config --global core.autocrlf input  # Mac/Linux
```

**Prevention:**
- Add .editorconfig file to project
- Use VS Code setting: `"files.eol": "\n"`
- Set git core.autocrlf on team machines

---

### 4. Long Path Issues

**Error Message:**
```
OSError: [WinError 206] The filename or extension is too long
```

**Cause:** Windows path exceeds 260 characters limit

**Solution:**
```powershell
# Enable long paths in Windows (requires reboot)
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force

# Or create project in shorter path:
# ❌ C:\Users\UserName\OneDrive\Documents\Very\Long\Nested\Path\ECOSURVEYCHat
# ✅ C:\Dev\ECOSURVEYCHat
```

**Prevention:**
- Keep project path short
- Enable long paths on development machines
- Document in setup guide

---

## Prevention Checklist

Use this before starting each new phase:

### Pre-Phase Checklist
- [ ] Python version is 3.10+ (`python --version`)
- [ ] Virtual environment activated (prompt shows `(.venv)`)
- [ ] All dependencies installed (`pip list | findstr fastapi`)
- [ ] PostgreSQL service running (`psql -U postgres -c "SELECT 1"`)
- [ ] Database exists (`psql -U postgres -d survey_chat -c "\dt"`)
- [ ] .env file exists and configured
- [ ] No syntax errors in modified files (IDE shows no red squiggles)
- [ ] Imports work: `python -c "from app.main import app"`

### Testing Checklist
- [ ] Run verification script: `python verify_phase1.py`
- [ ] Start API: `python -m uvicorn app.main:app --reload`
- [ ] Test health endpoint: `http://localhost:8000/health`
- [ ] View documentation: `http://localhost:8000/docs`
- [ ] Stop processes: `Stop-Process -Name python -Force`

### Code Quality Checklist
- [ ] Run formatter: `black app/`
- [ ] Check types: `mypy app/` (if configured)
- [ ] Check style: `flake8 app/` (if configured)
- [ ] Commit to git: `git add . && git commit -m "Phase X: description"`

---

## Adding New Errors

When encountering a new error in future phases:

1. **Document the error message** (exact text)
2. **Identify the cause** (why it happened)
3. **Provide the solution** (how to fix it)
4. **Add prevention tips** (how to avoid it next time)
5. **Update this file** with the new entry

---

## Quick Reference

| Error Type | Common Cause | Quick Fix |
|-----------|-------------|-----------|
| `ModuleNotFoundError` | Missing import or not in venv | Activate venv, `pip install -r requirements.txt` |
| `SyntaxError` | Missing colon, quote mismatch, indentation | Check IDE red squiggles, run formatter |
| `OperationalError` | PostgreSQL not running | `Start-Service -Name postgresql-x64-15` |
| `ProgrammingError` | Database/table doesn't exist | Run `python init_phase1.py` |
| `PydanticCustomError` | Missing/invalid request field | Check endpoint in Swagger UI `/docs` |
| `ImportError` | Circular import or wrong path | Check import order, use TYPE_CHECKING |
| `FileNotFoundError` | Wrong working directory | `cd` to project root, use absolute paths |
| `CORS blocked` | Frontend calling backend | Add CORSMiddleware to FastAPI app |

---

## Resources

- [FastAPI Debugging Guide](https://fastapi.tiangolo.com/advanced/debugging/)
- [SQLAlchemy Error Handling](https://docs.sqlalchemy.org/en/20/errors.html)
- [Pydantic Validation](https://docs.pydantic.dev/latest/concepts/validators/)
- [PostgreSQL Error Codes](https://www.postgresql.org/docs/current/errcodes.html)
- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)

---

*Last Updated: January 31, 2026*  
*Maintained by: Development Team*  
*Next Review: After Phase 2 completion*

