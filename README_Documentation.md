# Documentation Index - Economic Survey Practitioner Chat v1.2

## 📚 Document Structure

This project documentation is organized into the following files:

### **Core Specification Documents**
1. **[Spec_Doc.md](Spec_Doc.md)** - Complete product specification
   - Product requirements
   - Architecture design
   - Data model
   - API specifications
   - Security & privacy requirements

2. **[Development_Guide.md](Development_Guide.md)** - AI-led development principles
   - Prime directives
   - Ground rules for code generation
   - Build order
   - Stop conditions
   - Prompt templates for AI assistants

### **Planning & Orchestration**
3. **[Implementation_Plan.md](Implementation_Plan.md)** - Detailed implementation roadmap
   - 10-phase breakdown
   - Timeline estimates
   - Dependencies graph
   - Prerequisites checklist
   - Project structure

4. **[Orchestrator.md](Orchestrator.md)** - Coordination and execution guide
   - Phase sequencing logic
   - Stop condition protocols
   - Skill invocation strategy
   - Progress tracking
   - Error handling and rollback procedures

### **Skill Guides (How-To)**
Located in `Skills/` directory:

5. **Database_Skills.md** - Phase 1: Database setup
   - Project structure creation
   - SQL migrations
   - SQLAlchemy models
   - Docker configuration
   - API skeleton

6. **Auth_Skills.md** - Phase 2: Google OAuth
   - OAuth flow implementation
   - Pseudonymous ID generation
   - Session management
   - Privacy compliance

7. **XLSX_Ingestion_Skills.md** - Phase 3: Dataset ingestion
   - Workbook classification
   - Multi-panel detection
   - Multi-row headers
   - Number parsing
   - Long-format normalization

8. **Indicator_Skills.md** - Phase 4: (TODO)
9. **PDF_Ingestion_Skills.md** - Phase 5: (TODO)
10. **Summaries_Skills.md** - Phase 6: (TODO)
11. **Chat_Retrieval_Skills.md** - Phase 7: (TODO)
12. **Analytics_Skills.md** - Phase 8: (TODO)
13. **Frontend_Skills.md** - Phase 9: (TODO)
14. **Deployment_Skills.md** - Phase 10: (TODO)

### **Error Reference Guides**
Located in `Skills/` directory:

15. **Database_Common_Errors.md** - Phase 1 troubleshooting
16. **Auth_Common_Errors.md** - Phase 2 troubleshooting
17. **XLSX_Ingestion_Common_Errors.md** - Phase 3 troubleshooting (TODO)
18. Additional error guides for phases 4-10 (TODO)

---

## 🎯 How to Use This Documentation

### **For Developers**

**Starting a new phase:**
1. Read `Implementation_Plan.md` to understand phase goals
2. Review `Orchestrator.md` for dependencies and sequencing
3. Open the relevant `[Phase]_Skills.md` for step-by-step tasks
4. Keep `[Phase]_Common_Errors.md` open for troubleshooting

**When errors occur:**
1. Check the relevant `_Common_Errors.md` file first
2. If not found, check `Orchestrator.md` for error handling strategy
3. Consult `Spec_Doc.md` for clarification on requirements
4. Escalate if needed (see Orchestrator.md escalation path)

**Stop conditions:**
- Each phase has explicit stop conditions in its Skills guide
- If triggered, follow protocol in `Orchestrator.md`
- Do NOT proceed until resolved

### **For AI Assistants**

**Workflow:**
1. Load `Spec_Doc.md` and `Development_Guide.md` first
2. Check current phase status in todo list
3. Load relevant `[Phase]_Skills.md` for current phase
4. Follow task breakdown sequentially
5. Validate against acceptance criteria
6. Check stop conditions before marking complete

**Error handling:**
1. Search `[Phase]_Common_Errors.md` for symptom match
2. Apply solution from error guide
3. If unknown error, consult Orchestrator.md
4. Log error and resolution for future reference

### **For Project Managers**

**Progress tracking:**
- Check `Implementation_Plan.md` for overall timeline
- Review todo list for current phase status
- Use `Orchestrator.md` reporting template for status updates

**Risk management:**
- Monitor for stop conditions (see each Skills guide)
- Check error frequency in Common_Errors docs
- Review escalation path in `Orchestrator.md`

---

## 📊 Quick Reference

### **Phase Dependencies**
```
Phase 1 (Database)
    ├─→ Phase 2 (Auth)
    ├─→ Phase 3 (XLSX)
    │       └─→ Phase 4 (Indicators)
    └─→ Phase 5 (PDF)
            ↓
    Phases 3,4,5 complete
            ↓
        Phase 6 (Summaries)
            ↓
        Phase 7 (Chat)
            ├─→ Phase 8 (Analytics)
            └─→ Phase 9 (Frontend)
                    ↓
            Phase 10 (Deployment)
```

### **Stop Conditions Summary**

| Phase | Stop Condition |
|-------|---------------|
| 2 | Email/name/tokens stored in database |
| 3 | Multi-panel sheet not split |
| 5 | PDF ↔ XLSX references not linked |
| 6 | Claim card has zero evidence |
| 7 | Uncited numeric claims in responses |
| ANY | Runtime parsing of PDF/XLSX detected |

### **Key Principles**

1. **One-time ingestion only** - All parsing offline
2. **No PII storage** - Only pseudonymous IDs
3. **Practitioner responses** - Answer/Why/Evidence structure
4. **Evidence-grounded** - No hallucinated numbers
5. **Deterministic logic** - Fixed thresholds, no "tune later"

---

## 🔄 Documentation Status

### **Complete**
- ✅ Spec_Doc.md
- ✅ Development_Guide.md
- ✅ Implementation_Plan.md
- ✅ Orchestrator.md
- ✅ Database_Skills.md
- ✅ Database_Common_Errors.md
- ✅ Auth_Skills.md
- ✅ Auth_Common_Errors.md
- ✅ XLSX_Ingestion_Skills.md

### **In Progress**
- 🔄 XLSX_Ingestion_Common_Errors.md
- 🔄 Indicator_Skills.md
- 🔄 PDF_Ingestion_Skills.md

### **TODO**
- ⏳ Indicator_Common_Errors.md
- ⏳ PDF_Ingestion_Common_Errors.md
- ⏳ Summaries_Skills.md & Common_Errors.md
- ⏳ Chat_Retrieval_Skills.md & Common_Errors.md
- ⏳ Analytics_Skills.md & Common_Errors.md
- ⏳ Frontend_Skills.md & Common_Errors.md
- ⏳ Deployment_Skills.md & Common_Errors.md

---

## 📞 Support & Escalation

### **When to Escalate**

Escalate to the developer when:
- Stop condition cannot be resolved after multiple attempts
- Spec interpretation is ambiguous and affects architecture
- Missing critical credentials or data files
- Timeline risk exceeds 50% of phase estimate
- Security/privacy concerns arise

### **Escalation Template**

```markdown
**Phase:** [N]
**Issue:** [description]
**Stop Condition Triggered:** [yes/no]
**Attempts Made:** [list solutions tried]
**Blocker:** [what prevents progress]
**Request:** [specific help needed]
**Impact:** [timeline/quality impact]
```

---

## 🚀 Getting Started

**New to this project?**

1. Read [Spec_Doc.md](Spec_Doc.md) - Understand what we're building
2. Read [Development_Guide.md](Development_Guide.md) - Understand how we build
3. Read [Implementation_Plan.md](Implementation_Plan.md) - Understand the roadmap
4. Start with [Database_Skills.md](Skills/Database_Skills.md) - Begin Phase 1

**Ready to develop?**

1. Ensure prerequisites from Implementation_Plan.md are ready
2. Follow Orchestrator.md for phase sequencing
3. Use Skills guides as step-by-step instructions
4. Keep Common_Errors guides handy for troubleshooting

---

## 📝 Document Conventions

### **Symbols**
- ✅ Completed
- 🔄 In Progress
- ⏳ TODO
- 🚨 Critical/Stop Condition
- 🔗 Cross-reference
- 📋 Checklist
- 🎯 Goal/Objective
- 🛠️ Tool/Technology

### **Code Blocks**
- `inline code` - Commands, filenames, variables
- ```python - Python code examples
- ```sql - SQL queries
- ```bash - Shell commands
- ```yaml - Configuration files

### **Emphasis**
- **Bold** - Important concepts, stop conditions
- *Italic* - Notes, clarifications
- UPPERCASE - Critical warnings

---

## 📄 License & Usage

This documentation is for internal project use. All specifications and requirements are based on the Economic Survey Practitioner Chat v1.2 product requirements.

---

**Last Updated:** January 30, 2026
**Documentation Version:** 1.0
**Project Version:** v1.2
