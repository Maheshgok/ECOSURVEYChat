# Orchestrator Guide: Economic Survey Practitioner Chat

This document defines how to coordinate and execute the 10-phase implementation plan.

---

## 🎯 Role of the Orchestrator

The orchestrator is responsible for:
1. **Phase sequencing** - ensuring dependencies are met
2. **Stop condition enforcement** - halting on critical failures
3. **Skill coordination** - invoking the right skill at the right time
4. **Progress tracking** - maintaining todo list and phase status
5. **Quality gates** - validating deliverables before proceeding

---

## 📋 Phase Dependencies Graph

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
        Phases 7,8,9 complete
                    ↓
            Phase 10 (Deployment)
```

**Key insights:**
- Phases 2, 3, 5 can run in parallel after Phase 1
- Phase 4 depends only on Phase 3
- Phase 6 requires Phases 3, 4, and 5
- Phases 8 and 9 can run in parallel after Phase 7

---

## 🔄 Execution Workflow

### **Pre-Phase Checklist**
Before starting any phase:
1. ✅ Check all dependencies are complete
2. ✅ Verify required credentials/files are available
3. ✅ Review skill guide for the phase
4. ✅ Review common errors for the phase
5. ✅ Update todo list to "in-progress"

### **During Phase Execution**
1. Follow the skill guide step-by-step
2. Run validation tests after each major task
3. Check outputs against acceptance criteria
4. If error occurs, consult common errors guide
5. If stop condition triggered, halt immediately and report

### **Post-Phase Validation**
Before marking phase complete:
1. ✅ All deliverables produced
2. ✅ All acceptance tests pass
3. ✅ No stop conditions violated
4. ✅ Code committed to repository
5. ✅ Update todo list to "completed"

---

## 🚦 Stop Condition Protocol

### **What is a Stop Condition?**
A non-negotiable requirement that, if violated, must halt all development until fixed.

### **Stop Conditions by Phase**

| Phase | Stop Condition | Action |
|-------|---------------|--------|
| 2 | Google login stores email/name/tokens | Delete all PII, fix auth flow, retest |
| 3 | XLSX doesn't split multi-panel sheets | Fix panel detection logic, rerun on test file |
| 5 | PDF references don't link to XLSX | Fix cross-linking logic, rebuild edges |
| 6 | Claim card has zero evidence citations | Regenerate claim cards with evidence requirement |
| 7 | Chat response contains uncited numbers | Fix response validation, add citation enforcement |
| ANY | Runtime parsing of PDF/XLSX detected | Move parsing to ingestion, remove from runtime |

### **When Stop Condition Triggers**
1. **STOP** all development immediately
2. **LOG** the violation with details
3. **NOTIFY** the developer
4. **FIX** the root cause (not just symptoms)
5. **RETEST** with explicit validation
6. **RESUME** only after confirmed fix

---

## 🔧 Skill Invocation Strategy

### **Sequential Phases (must complete in order)**
- Phase 1 → Phase 2
- Phase 3 → Phase 4
- Phase 6 → Phase 7 → Phase 10

**Strategy:** Complete each phase fully before starting the next.

### **Parallel Phases (can run simultaneously)**
After Phase 1:
- Phase 2 (Auth) + Phase 3 (XLSX) + Phase 5 (PDF)

After Phase 7:
- Phase 8 (Analytics) + Phase 9 (Frontend)

**Strategy:** Start parallel phases together, but wait for all to complete before proceeding.

---

## 📊 Progress Tracking

### **Todo List States**
- `not-started` - Phase not begun
- `in-progress` - Currently working on this phase (max 1 at a time unless parallel)
- `completed` - Phase fully validated and deliverables confirmed

### **Phase Completion Criteria**

Each phase is marked complete only when:
1. All tasks in skill guide completed
2. All deliverables produced and verified
3. All acceptance tests pass
4. No stop conditions triggered
5. Code pushed to repository

### **Reporting Template**

```markdown
## Phase [N] Status: [in-progress/completed]

**Tasks Completed:** X / Y
**Tests Passed:** X / Y
**Deliverables:** [list]
**Blockers:** [none/list]
**Next Steps:** [description]
```

---

## 🎓 Skill Selection Guide

| Phase | Primary Skill | Supporting Skills |
|-------|--------------|-------------------|
| 1 | Database_Skills | - |
| 2 | Auth_Skills | Database_Skills |
| 3 | XLSX_Ingestion_Skills | Database_Skills |
| 4 | Indicator_Skills | XLSX_Ingestion_Skills, Database_Skills |
| 5 | PDF_Ingestion_Skills | Database_Skills |
| 6 | Summaries_Skills | PDF_Ingestion_Skills, XLSX_Ingestion_Skills, Indicator_Skills |
| 7 | Chat_Retrieval_Skills | PDF_Ingestion_Skills, Indicator_Skills, Summaries_Skills |
| 8 | Analytics_Skills | Chat_Retrieval_Skills, Database_Skills |
| 9 | Frontend_Skills | Chat_Retrieval_Skills, Auth_Skills |
| 10 | Deployment_Skills | All previous skills |

---

## 🐛 Error Handling Strategy

### **When an error occurs:**

1. **Classify the error:**
   - Syntax error → Fix immediately
   - Logic error → Check skill guide
   - Stop condition → Follow stop protocol
   - Unknown → Check common errors guide

2. **Consult the right guide:**
   - Skill-specific error → `[Skill]_Common_Errors.md`
   - Cross-phase error → This orchestrator guide
   - Spec interpretation → Spec_Doc.md + Development_Guide.md

3. **Resolution paths:**
   - **Quick fix:** Apply and continue
   - **Requires rework:** Rollback to last stable state
   - **Stop condition:** Halt and fix per protocol
   - **Design clarification:** Consult spec, assume deterministic defaults

---

## 🔄 Rollback Strategy

### **When to Rollback**

Rollback to the last completed phase when:
- Multiple consecutive failures in current phase
- Stop condition cannot be fixed without rearchitecture
- Data corruption detected in database
- Integration test failures after phase completion

### **Rollback Procedure**

1. Identify last stable phase
2. Restore database to that phase's state
3. Restore codebase to that commit
4. Re-validate that phase's acceptance tests
5. Analyze root cause before retrying

---

## 📈 Success Metrics

### **Phase-Level Metrics**
- Time to complete vs estimated
- Number of errors encountered
- Stop conditions triggered (should be 0)
- Tests passed on first attempt

### **Project-Level Metrics**
- Total implementation time
- Code quality (lint/format compliance)
- Test coverage (ingestion scripts + API)
- Documentation completeness

---

## 🚀 Phase Kickoff Checklist

Before starting Phase N:

```markdown
[ ] All dependencies (phases) completed
[ ] Required data files available
[ ] Required credentials available
[ ] Skill guide reviewed
[ ] Common errors guide reviewed
[ ] Development environment ready
[ ] Tests from previous phases still passing
[ ] Todo list updated to "in-progress"
```

---

## ✅ Phase Signoff Checklist

Before marking Phase N complete:

```markdown
[ ] All tasks completed
[ ] All deliverables produced
[ ] All acceptance tests pass
[ ] No stop conditions triggered
[ ] Code formatted and linted
[ ] Code committed to repository
[ ] Documentation updated
[ ] Todo list updated to "completed"
[ ] Next phase dependencies verified
```

---

## 🎯 Final Acceptance (Phase 10)

Before declaring the project complete:

```markdown
[ ] All 10 phases marked completed
[ ] Backend deployed to GCP
[ ] Frontend deployed to Netlify
[ ] End-to-end tests pass
[ ] Stop condition validations pass
[ ] Acceptance tests from spec pass:
    [ ] XLSX panel split works
    [ ] PDF ↔ XLSX linking works
    [ ] Chat responses structured correctly
    [ ] No PII stored in database
[ ] Admin can access analytics
[ ] Documentation complete
[ ] Handoff materials ready
```

---

## 📞 Escalation Path

### **When to Escalate**

Escalate to the developer when:
- Stop condition cannot be resolved
- Multiple rollbacks required
- Spec interpretation is ambiguous and affects architecture
- Missing critical credentials/data
- Timeline risk exceeds 50% of phase estimate

### **Escalation Template**

```markdown
**Phase:** [N]
**Issue:** [description]
**Stop Condition:** [yes/no]
**Attempts Made:** [list]
**Blocker:** [what prevents progress]
**Request:** [what you need to proceed]
```

---

**Orchestrator Principle:** *"Slow is smooth, smooth is fast. Validate at every step."*
