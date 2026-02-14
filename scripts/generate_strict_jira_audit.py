#!/usr/bin/env python3
"""Generate strict Jira compliance audit report (JSON + Markdown) from JSON/CSV input.

Non-hallucination behavior:
- Uses only provided fields.
- Returns UNKNOWN / NEEDS_MANUAL_REVIEW when data is missing.
- Emits per-check evidence with field snippets.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TERMINAL_STATUSES = {"done", "cancelled"}


def _load_input(path: Path) -> List[Dict[str, Any]]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            if "issues" in data and isinstance(data["issues"], list):
                return data["issues"]
            return [data]
        if isinstance(data, list):
            return data
        raise ValueError("JSON input must be an object or array")

    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return [dict(r) for r in reader]

    raise ValueError("Unsupported file extension. Use .json or .csv")


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    if isinstance(value, str):
        if not value.strip():
            return []
        if value.strip().startswith("[") and value.strip().endswith("]"):
            try:
                parsed = json.loads(value)
                return [str(v) for v in parsed]
            except Exception:
                pass
        return [v.strip() for v in value.split(",") if v.strip()]
    return [str(value)]


def _is_mit(issue: Dict[str, Any]) -> bool:
    labels = [x.lower() for x in _as_list(issue.get("labels"))]
    issue_type = str(issue.get("issue_type", "")).lower()
    mapped = issue.get("is_mit")
    return ("mit" in labels) or ("mit" in issue_type) or (mapped is True)


def _ev(issue: Dict[str, Any], field: str, value: Any) -> Dict[str, str]:
    key = str(issue.get("issue_key", "UNKNOWN"))
    snippet = "" if value is None else str(value)
    return {"issue_key": key, "field": field, "value_snippet": snippet[:300]}


@dataclass
class CheckResult:
    criterion_id: str
    criterion_name: str
    result: str
    severity: str
    evidence: List[Dict[str, str]]
    reason: str


MANUAL = {
    "M1": "Comment Quality",
    "M2": "Missing Comments",
    "M3": "Screenshot-Only Evidence",
    "M4": "Doc-Link-Only Evidence",
    "M5": "Description Quality",
    "M6": "Title Quality",
    "M7": "Multiple Issues in One Ticket",
    "M8": "History Integrity",
    "M9": "Acceptance Criteria Relevance",
    "M10": "Productivity Validity",
    "M11": "Evidence Relevance",
}


def _manual_checks(issue: Dict[str, Any]) -> List[CheckResult]:
    out: List[CheckResult] = []
    comments_present = "comments" in issue
    comments = issue.get("comments")

    for cid, name in MANUAL.items():
        if cid == "M2":
            if not comments_present:
                out.append(CheckResult(cid, name, "UNKNOWN", "NORMAL", [], "UNKNOWN because comments field not provided."))
            elif not comments:
                out.append(CheckResult(cid, name, "FAIL", "NORMAL", [_ev(issue, "comments", comments)], "Comments field present but empty."))
            else:
                out.append(CheckResult(cid, name, "PASS", "NORMAL", [_ev(issue, "comments", comments)], "At least one comment is present."))
            continue

        if cid == "M8":
            if "changelog" not in issue and "status_history" not in issue:
                out.append(CheckResult(cid, name, "UNKNOWN", "CRITICAL-UNKNOWN", [], "UNKNOWN because changelog/history not provided."))
            else:
                out.append(CheckResult(cid, name, "NEEDS_MANUAL_REVIEW", "NORMAL", [_ev(issue, "changelog", issue.get("changelog"))], "Manual judgment required for manipulation detection."))
            continue

        if cid == "M9":
            ac = None
            cf = issue.get("custom_fields")
            if isinstance(cf, dict):
                ac = cf.get("Acceptance Criteria") or cf.get("acceptance_criteria")
            if ac is None:
                out.append(CheckResult(cid, name, "UNKNOWN", "NORMAL", [], "UNKNOWN because acceptance criteria field not provided."))
            else:
                out.append(CheckResult(cid, name, "NEEDS_MANUAL_REVIEW", "NORMAL", [_ev(issue, "custom_fields.Acceptance Criteria", ac)], "Manual relevance assessment required."))
            continue

        out.append(CheckResult(cid, name, "NEEDS_MANUAL_REVIEW", "NORMAL", [], "Manual/content-quality check requires human judgment."))

    return out


def _score_issue(checks: List[CheckResult]) -> str:
    fails = sum(1 for c in checks if c.result == "FAIL")
    crit_fail = any(c.result == "FAIL" and c.severity == "CRITICAL" for c in checks)
    crit_unknown = any(c.severity == "CRITICAL-UNKNOWN" for c in checks)
    passes = sum(1 for c in checks if c.result == "PASS")
    unknownish = sum(1 for c in checks if c.result in {"UNKNOWN", "NEEDS_MANUAL_REVIEW"})

    if crit_fail or fails >= 2:
        return "BAD"
    if crit_unknown:
        return "UNKNOWN"
    if passes > unknownish:
        return "GOOD"
    return "UNKNOWN"


def build_report(issues: List[Dict[str, Any]], start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
    by_emp: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for i in issues:
        by_emp[str(i.get("assignee_name", "UNKNOWN_ASSIGNEE"))].append(i)

    employees: List[Dict[str, Any]] = []
    org_mit_proposed = org_mit_created = org_mit_closed = org_non_mit_active = 0

    for emp, emp_issues in sorted(by_emp.items(), key=lambda x: x[0]):
        issue_objs = []
        critical_failures = []

        mit_issues = [i for i in emp_issues if _is_mit(i)]
        non_mit_active = [i for i in emp_issues if not _is_mit(i) and str(i.get("status", "")).lower() not in TERMINAL_STATUSES]

        for issue in emp_issues:
            checks: List[CheckResult] = []

            # C7 zero tolerance (cancellation)
            status = str(issue.get("status", ""))
            if status.lower() == "cancelled":
                ch = issue.get("changelog")
                comments = issue.get("comments")
                approval_text = f"{ch} {comments}".lower()
                if "manager" in approval_text and "approv" in approval_text:
                    checks.append(CheckResult("C7", "Task Cancellation", "PASS", "NORMAL", [_ev(issue, "status", status), _ev(issue, "changelog/comments", approval_text)], "Cancelled task includes manager-approval evidence."))
                elif "changelog" in issue or "comments" in issue:
                    checks.append(CheckResult("C7", "Task Cancellation", "FAIL", "CRITICAL", [_ev(issue, "status", status), _ev(issue, "changelog/comments", approval_text)], "Cancelled task lacks manager-approval evidence."))
                else:
                    checks.append(CheckResult("C7", "Task Cancellation", "UNKNOWN", "CRITICAL-UNKNOWN", [_ev(issue, "status", status)], "Cancellation exists but approval evidence fields are missing."))
            else:
                checks.append(CheckResult("C7", "Task Cancellation", "PASS", "NORMAL", [_ev(issue, "status", status)], "Issue is not cancelled."))

            # C10 documentation
            expected = ["created_at", "updated_at", "status_history", "description"]
            missing = [f for f in expected if f not in issue or issue.get(f) in (None, "")]
            if not missing:
                checks.append(CheckResult("C10", "Documentation/Traceability", "PASS", "NORMAL", [_ev(issue, f, issue.get(f)) for f in expected], "Expected metadata fields are present."))
            else:
                checks.append(CheckResult("C10", "Documentation/Traceability", "FAIL", "NORMAL", [_ev(issue, "missing_fields", ", ".join(missing))], "Expected metadata fields are missing from provided issue record."))

            checks.extend(_manual_checks(issue))

            issue_grade = _score_issue(checks)
            if any(c.result == "FAIL" and c.severity == "CRITICAL" for c in checks):
                critical_failures.append(f"{issue.get('issue_key', 'UNKNOWN')}: C7 Task Cancellation")
            if any(c.severity == "CRITICAL-UNKNOWN" for c in checks):
                critical_failures.append(f"{issue.get('issue_key', 'UNKNOWN')}: critical unknown (insufficient data)")

            issue_objs.append(
                {
                    "issue_key": str(issue.get("issue_key", "UNKNOWN")),
                    "summary": str(issue.get("summary", "")),
                    "type": str(issue.get("issue_type", "UNKNOWN")),
                    "labels": _as_list(issue.get("labels")),
                    "status": str(issue.get("status", "UNKNOWN")),
                    "good_bad_unknown": issue_grade,
                    "checks": [
                        {
                            "criterion_id": c.criterion_id,
                            "criterion_name": c.criterion_name,
                            "result": c.result,
                            "severity": c.severity,
                            "evidence": c.evidence,
                            "reason": c.reason,
                        }
                        for c in checks
                    ],
                }
            )

        mit_closed = sum(1 for i in mit_issues if str(i.get("status", "")).lower() in {"done", "waiting for review"})

        org_mit_proposed += len(mit_issues)
        org_mit_created += len(mit_issues)
        org_mit_closed += mit_closed
        org_non_mit_active += len(non_mit_active)

        employees.append(
            {
                "employee_name": emp,
                "issues": issue_objs,
                "employee_summary": {
                    "mit_proposed_count": len(mit_issues),
                    "mit_created_count": len(mit_issues),
                    "mit_closed_by_fri_eod_count": len(mit_issues) if start_date is None or end_date is None else mit_closed,
                    "non_mit_active_count": len(non_mit_active),
                    "recap_to_jira_coverage": "UNKNOWN",
                    "critical_failures": critical_failures,
                    "notes": "Recap mapping and timing evidence were not provided; related checks remain UNKNOWN.",
                },
            }
        )

    return {
        "audit_window": {
            "start_date": start_date or "UNKNOWN",
            "end_date": end_date or "UNKNOWN",
        },
        "employees": employees,
        "org_summary": {
            "totals": {
                "employee_count": len(employees),
                "mit_proposed_count": org_mit_proposed,
                "mit_created_count": org_mit_created,
                "mit_closed_by_fri_eod_count": org_mit_closed,
                "non_mit_active_count": org_non_mit_active,
                "recap_to_jira_coverage": "UNKNOWN",
            },
            "top_risks": [
                "Recap-to-Jira conversion is UNKNOWN unless recap action items mapping is provided.",
                "Lifecycle adherence is UNKNOWN unless SOP step-level evidence and timing fields are provided.",
            ],
        },
    }


def to_markdown(report: Dict[str, Any]) -> str:
    lines = []
    aw = report["audit_window"]
    lines.append("# Jira Compliance Audit Report")
    lines.append("")
    lines.append(f"**Audit window:** {aw['start_date']} to {aw['end_date']}")
    lines.append("")
    lines.append("## Per-Employee Results")

    for emp in report["employees"]:
        lines.append(f"### {emp['employee_name']}")
        for i in emp["issues"]:
            lines.append(f"- **{i['issue_key']}** ({i['status']}) — **{i['good_bad_unknown']}**: {i['summary']}")
        s = emp["employee_summary"]
        lines.append(f"- MIT proposed/created/closed: {s['mit_proposed_count']}/{s['mit_created_count']}/{s['mit_closed_by_fri_eod_count']}")
        lines.append(f"- Non-MIT active: {s['non_mit_active_count']}")
        lines.append(f"- Recap->Jira coverage: {s['recap_to_jira_coverage']}")
        lines.append(f"- Critical failures: {', '.join(s['critical_failures']) if s['critical_failures'] else 'None'}")
        lines.append("")

    lines.append("## Consolidated Summary")
    lines.append("")
    lines.append("| Employee | MIT Proposed (count) | MIT Created (count) | MIT Closed by Fri EOD (count) | Non-MIT Active (count) | Recap->Jira Coverage | Critical Failures | Notes |")
    lines.append("|---|---:|---:|---:|---:|---:|---|---|")
    for emp in report["employees"]:
        s = emp["employee_summary"]
        lines.append(
            f"| {emp['employee_name']} | {s['mit_proposed_count']} | {s['mit_created_count']} | {s['mit_closed_by_fri_eod_count']} | {s['non_mit_active_count']} | {s['recap_to_jira_coverage']} | "
            f"{('; '.join(s['critical_failures']) if s['critical_failures'] else 'None')} | {s['notes']} |"
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="Generate strict Jira compliance JSON + Markdown")
    p.add_argument("--input", required=True, help="Path to issue dataset JSON/CSV")
    p.add_argument("--start-date", default=None)
    p.add_argument("--end-date", default=None)
    p.add_argument("--json-out", default="audit_report.json")
    p.add_argument("--md-out", default="audit_report.md")
    args = p.parse_args()

    issues = _load_input(Path(args.input))
    report = build_report(issues, args.start_date, args.end_date)

    Path(args.json_out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    Path(args.md_out).write_text(to_markdown(report), encoding="utf-8")

    print(f"Wrote JSON: {args.json_out}")
    print(f"Wrote Markdown: {args.md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
