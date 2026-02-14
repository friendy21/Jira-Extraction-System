## Jira Compliance Audit Report

### Audit Window
- **Start Date:** UNKNOWN  
- **End Date:** UNKNOWN  
- **Why unknown:** Input did not include explicit `start_date` / `end_date` audit window fields.

## Per-Employee Findings

### Employee: **Bendangtila.Jamir**

#### Issues in scope
1. **OH-197** — Summary UNKNOWN (not provided)

**Issue verdict:** **BAD**  
Reason: Multiple explicit FAIL checks (C6, C8, C9, C11) and zero-tolerance checks unresolved with missing evidence (CRITICAL-UNKNOWN).

#### Criterion results (evidence-based)
- **C6 Status Hygiene:** **FAIL**  
  Evidence: `status_hygiene = "No - Invalid transition: OH-197: Backlog → to do"`
- **C8 Weekly Updates:** **FAIL**  
  Evidence: `update_frequency = "No"`
- **C9 Roles & Access:** **FAIL**  
  Evidence: `role_ownership = "No - Reporter = Assignee"`
- **C10 Documentation/Traceability:** **UNKNOWN**  
  Evidence: `documentation = "Error"`
- **C11 Lifecycle Adherence:** **FAIL**  
  Evidence: `lifecycle = "No - OH-197: Skipped In Progress"`
- **C7 Task Cancellation (Zero Tolerance):** **UNKNOWN** → **CRITICAL-UNKNOWN**  
  Evidence: `cancellation = "No"`, `zero_tolerance = "Yes"`, auditor note includes `"Zero-tolerance violation detected"`; no approval/status-history record provided.
- **M8 History Integrity (Zero Tolerance):** **UNKNOWN** → **CRITICAL-UNKNOWN**  
  Evidence: changelog/history data not provided.

#### Employee Compliance Summary
- MIT Proposed: **UNKNOWN**
- MIT Created: **UNKNOWN**
- MIT Closed by Fri EOD: **UNKNOWN**
- Non-MIT Active: **UNKNOWN**
- Recap→Jira Coverage: **UNKNOWN**
- Critical flags:
  - C7 Task Cancellation: CRITICAL-UNKNOWN
  - M8 History Integrity: CRITICAL-UNKNOWN

---

## Consolidated Summary Table

| Employee | MIT Proposed (count) | MIT Created (count) | MIT Closed by Fri EOD (count) | Non-MIT Active (count) | Recap->Jira Coverage | Critical Failures | Notes |
|---|---:|---:|---:|---:|---|---|---|
| Bendangtila.Jamir | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | C7 (CRITICAL-UNKNOWN), M8 (CRITICAL-UNKNOWN) | Aggregate-only dataset; detailed issue metadata missing |

---

## Data Gaps / Non-Hallucination Notes
- UNKNOWN because missing: detailed issue records (beyond OH-197 references), labels, MIT approval list, status transition timestamps, comments payload, attachments/link context, changelog entries, recap action-item mapping, and explicit audit-week window fields.
- NEEDS_MANUAL_REVIEW not applied where objective field-level evidence already indicated explicit FAIL strings in the provided dataset.
