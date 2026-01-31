# Project Kickoff Checklist - Economic Survey Practitioner Chat

**Date:** January 30, 2026  
**Project:** Economic Survey Practitioner Chat v1.2  
**Developer:** [Your Name]

---

## 📋 Documentation Created

### ✅ Core Documentation (Complete)
- [x] **Implementation_Plan.md** - 10-phase implementation roadmap
- [x] **Orchestrator.md** - Phase coordination and execution guide
- [x] **README_Documentation.md** - Documentation index and navigation guide

### ✅ Skills Guides (Phase 1-3 Complete)
- [x] **Skills/Database_Skills.md** - Phase 1 detailed tasks
- [x] **Skills/Auth_Skills.md** - Phase 2 detailed tasks
- [x] **Skills/XLSX_Ingestion_Skills.md** - Phase 3 detailed tasks

### ✅ Error Reference Guides (Phase 1-2 Complete)
- [x] **Skills/Database_Common_Errors.md** - Phase 1 troubleshooting
- [x] **Skills/Auth_Common_Errors.md** - Phase 2 troubleshooting

### ⏳ Pending Documentation (Phases 4-10)
- [ ] Skills/Indicator_Skills.md
- [ ] Skills/PDF_Ingestion_Skills.md
- [ ] Skills/Summaries_Skills.md
- [ ] Skills/Chat_Retrieval_Skills.md
- [ ] Skills/Analytics_Skills.md
- [ ] Skills/Frontend_Skills.md
- [ ] Skills/Deployment_Skills.md
- [ ] Corresponding Common_Errors.md files for each

**Note:** These will be created as needed when starting each phase.

---

## 🔑 Prerequisites to Gather

Before starting development, you need:

### **1. Source Data Files**
- [ ] Economic Survey PDF(s)
  - Preferred: Full volume PDF
  - Alternative: Chapter-wise PDFs
- [ ] Economic Survey XLSX datasets
  - Specifically need: `tabchart1.xlsx` (multi-panel test)
  - Specifically need: `tab1.1.xlsx` (big table test)
  - All other dataset files in a directory
- [ ] Supplementary reports (PDF/DOCX) - optional

**Where to get:** [Specify source/provide links]

### **2. GCP Setup**
- [ ] GCP Project created
  - Project ID: ___________________
  - Project Name: ___________________
- [ ] Service account created with permissions:
  - [ ] Cloud SQL Admin
  - [ ] Cloud Run Admin (or Compute Engine Admin)
  - [ ] Storage Admin (if using Cloud Storage)
- [ ] Service account JSON key downloaded
  - Path: ___________________
- [ ] Preferred region selected: ___________________
  - Recommended: `us-central1` or `asia-south1`

**Action:** Save GCP project ID and service account key securely.

### **3. Google OAuth Credentials**
- [ ] Google Cloud Console project configured for OAuth
  - Use same project as above or separate: ___________________
- [ ] OAuth 2.0 Client ID created (Web application type)
- [ ] Authorized JavaScript origins configured:
  - [ ] `http://localhost:8000` (development)
  - [ ] Production API URL: ___________________
- [ ] Authorized redirect URIs configured:
  - [ ] `http://localhost:8000/auth/callback`
  - [ ] Production callback URL: ___________________
- [ ] Credentials obtained:
  - [ ] `GOOGLE_CLIENT_ID`: ___________________
  - [ ] `GOOGLE_CLIENT_SECRET`: ___________________

**Action:** Store these in a secure location for `.env` file.

### **4. LLM API Credentials**
- [ ] OpenAI account OR Anthropic account
- [ ] API key generated
  - Provider: [ ] OpenAI  [ ] Anthropic
  - API Key: ___________________
- [ ] Model selected:
  - Chat model: ___________________ (e.g., gpt-4o, claude-3-5-sonnet)
  - Embedding model: ___________________ (e.g., text-embedding-3-large)
- [ ] Usage limits/budget configured (optional): ___________________

**Action:** Test API key works before starting Phase 6.

### **5. GitHub Repository**
- [ ] GitHub account: ___________________
- [ ] Repository created
  - Name: ___________________
  - URL: ___________________
  - Visibility: [ ] Public  [ ] Private
- [ ] Local Git configured
  - [ ] `git config --global user.name "..."`
  - [ ] `git config --global user.email "..."`

**Action:** Initialize repository with README before Phase 1.

### **6. Generated Secrets**
Generate these values and store securely:

```bash
# Generate SERVER_SALT (for pseudonymous IDs)
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
- [ ] `SERVER_SALT`: ___________________

```bash
# Generate SESSION_SECRET (for cookie signing)
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
- [ ] `SESSION_SECRET`: ___________________

**Action:** Add to `.env` file when setting up Phase 1.

### **7. Netlify Setup**
- [ ] Netlify account: ___________________
- [ ] Connect GitHub repository to Netlify
- [ ] Site name: ___________________ (e.g., ecosurvey-chat)
- [ ] Custom domain (optional): ___________________

**Action:** Will configure in Phase 9 (Frontend).

### **8. Development Environment**
- [ ] Docker Desktop installed and running
- [ ] Python 3.11+ installed
- [ ] VS Code (or preferred IDE) installed
- [ ] Git installed
- [ ] Node.js installed (for potential frontend tooling)

**System:** Windows (confirmed from context)

---

## 🚀 Ready to Start Checklist

### **Immediate (to start Phase 1)**
- [ ] Documentation read and understood:
  - [ ] Spec_Doc.md reviewed
  - [ ] Development_Guide.md reviewed
  - [ ] Implementation_Plan.md reviewed
  - [ ] Orchestrator.md reviewed
- [ ] Development environment ready:
  - [ ] Docker running
  - [ ] Python 3.11+ available
  - [ ] Git configured
- [ ] GitHub repository created and cloned locally

**Can start Phase 1 with just these ✓**

### **For Phase 2 (Auth)**
- [ ] Google OAuth credentials ready
- [ ] `SERVER_SALT` and `SESSION_SECRET` generated

### **For Phase 3 (XLSX Ingestion)**
- [ ] `tabchart1.xlsx` available (must have multi-panel sheet)
- [ ] `tab1.1.xlsx` available (must have big time-series table)
- [ ] Other XLSX dataset files collected

### **For Phase 5 (PDF Ingestion)**
- [ ] Economic Survey PDF(s) available

### **For Phase 6 (Summaries)**
- [ ] LLM API key ready and tested

### **For Phase 10 (Deployment)**
- [ ] GCP project fully configured
- [ ] Cloud SQL instance created (or will create in Phase 10)
- [ ] Netlify site configured

---

## 📊 Project Structure to Create

Once starting Phase 1, create this structure:

```
survey-practitioner-chat/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── dependencies.py
│   │   │   └── sessions.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── corpus.py
│   │   │   ├── document.py
│   │   │   ├── node.py
│   │   │   ├── edge.py
│   │   │   ├── data.py
│   │   │   ├── indicator.py
│   │   │   ├── summary.py
│   │   │   ├── search.py
│   │   │   ├── analytics.py
│   │   │   └── user.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── auth.py
│   │   │   ├── chat.py
│   │   │   ├── corpus.py
│   │   │   ├── evidence.py
│   │   │   └── admin.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── auth_service.py
│   │       ├── retrieval_service.py
│   │       └── llm_service.py
│   ├── migrations/
│   │   └── 001_init.sql
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env
│   └── .env.example
├── ingestion/
│   ├── __init__.py
│   ├── pdf_ingest.py
│   ├── xlsx_ingest.py
│   ├── indicators.py
│   ├── summaries.py
│   ├── label_messages.py
│   ├── cluster_topics.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── summary.html
│   ├── chat.html
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   ├── auth.js
│   │   ├── summary.js
│   │   ├── chat.js
│   │   └── evidence.js
│   └── netlify.toml
├── docs/
│   ├── Implementation_Plan.md
│   ├── Orchestrator.md
│   ├── README_Documentation.md
│   └── Skills/
│       ├── Database_Skills.md
│       ├── Auth_Skills.md
│       └── ... (other skill guides)
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## 🎯 Next Steps

### **Step 1: Repository Setup**
```bash
# Create repository on GitHub
# Clone locally
git clone https://github.com/[your-username]/[repo-name].git
cd [repo-name]

# Copy documentation
mkdir docs
cp [path-to-docs]/*.md docs/
cp -r [path-to-docs]/Skills docs/

# Initial commit
git add .
git commit -m "Initial commit: Project documentation"
git push origin main
```

### **Step 2: Gather Prerequisites**
- Work through the checklist above
- Store credentials securely (password manager recommended)
- Create `.env.example` template (no real values)

### **Step 3: Start Phase 1**
```bash
# Once ready, follow Database_Skills.md
# Create project structure
# Set up docker-compose.yml
# Create migrations
# Create models
# Test with docker-compose up
```

### **Step 4: Continuous Progress Tracking**
- Update todo list after each phase
- Follow Orchestrator.md for phase transitions
- Check stop conditions before proceeding
- Document any deviations or issues

---

## 🚨 Important Reminders

### **Privacy & Security**
- ✅ NEVER commit real credentials to Git
- ✅ Use `.env` for secrets (add to `.gitignore`)
- ✅ Verify no PII stored after Phase 2
- ✅ Use pseudonymous IDs only

### **Stop Conditions**
- 🚨 Phase 2: No email/name in database
- 🚨 Phase 3: Multi-panel split must work
- 🚨 Phase 5: PDF ↔ XLSX links must exist
- 🚨 Phase 6: All claims must have evidence
- 🚨 Phase 7: No uncited numbers
- 🚨 ANY: No runtime PDF/XLSX parsing

### **Architecture Principles**
- One-time ingestion offline
- Runtime is retrieval + response only
- Deterministic logic, no "tune later"
- Practitioner tone always
- Evidence-grounded responses

---

## 📞 Support Resources

**Documentation:**
- Start with `README_Documentation.md` for navigation
- Skill guides for step-by-step instructions
- Common_Errors guides for troubleshooting

**When Stuck:**
1. Check relevant Common_Errors.md
2. Review Orchestrator.md error handling
3. Consult Spec_Doc.md for requirements
4. Escalate if needed (see Orchestrator.md)

**External Resources:**
- FastAPI docs: https://fastapi.tiangolo.com
- SQLAlchemy docs: https://docs.sqlalchemy.org
- pgvector docs: https://github.com/pgvector/pgvector
- Authlib docs: https://docs.authlib.org
- openpyxl docs: https://openpyxl.readthedocs.io

---

## ✅ Completion Criteria

Project is complete when:
- [ ] All 10 phases marked "completed" in todo list
- [ ] Backend deployed to GCP
- [ ] Frontend deployed to Netlify
- [ ] End-to-end tests pass
- [ ] All stop condition validations pass
- [ ] Documentation complete
- [ ] Handoff materials ready

---

**Good luck! Follow the guides, check stop conditions, and build iteratively.** 🚀
