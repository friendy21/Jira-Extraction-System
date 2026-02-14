"""
Audit Report Builder Module
Generates detailed ticket-by-ticket JIRA compliance audit reports.

Implements the Senior Compliance Auditor role:
- Evaluates individual tickets against 22 compliance criteria
- Generates executive summary with compliance metrics
- Produces detailed ticket-by-ticket breakdown
- Groups failures into actionable recommendations
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import yaml

from src.compliance.checks import (
    # Existing checks
    StatusHygieneCheck,
    CancellationCheck,
    UpdateFrequencyCheck,
    RoleOwnershipCheck,
    DocumentationCheck,
    LifecycleCheck,
    ZeroToleranceCheck,
    # New checks (to be implemented)
    MITPlanningCheck,
    MITCreationCheck,
    MITCompletionCheck,
    NonMITTrackingCheck,
    RecapToJiraConversionCheck,
    CommentQualityCheck,
    MissingCommentsCheck,
    ScreenshotOnlyEvidenceCheck,
    DocLinkOnlyEvidenceCheck,
    DescriptionQualityCheck,
    TitleQualityCheck,
    MultipleIssuesCheck,
    HistoryIntegrityCheck,
    AcceptanceCriteriaRelevanceCheck,
    ProductivityValidityCheck,
    EvidenceRelevanceCheck,
)
from src.jira_client import JiraClient
from src.database.connection import get_session
from src.database.models import JiraUser
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AuditReportBuilder:
    """
    Builds detailed JIRA compliance audit reports.
    
    Generates markdown/JSON/Excel reports with:
    - Executive summary (total audited, compliant %, zero-tolerance violations)
    - Detailed ticket-by-ticket breakdown with pass/fail per criterion
    - Grouped recommendations with actionable fixes
    """
    
    def __init__(self, jira_client: JiraClient, output_dir: str = "./outputs/audit_reports"):
        """
        Initialize audit report builder.
        
        Args:
            jira_client: Authenticated JIRA client instance
            output_dir: Directory for output files
        """
        self.jira_client = jira_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load compliance criteria configuration
        config_path = Path("config/compliance_criteria.yaml")
        with open(config_path, 'r', encoding='utf-8') as f:
            self.criteria_config = yaml.safe_load(f)
        
        # Initialize all compliance checks
        self._initialize_compliance_checks()
        
        logger.info(f"Audit report builder initialized with {len(self.all_checks)} compliance checks")
    
    def _initialize_compliance_checks(self):
        """Initialize all compliance check instances."""
        # Core process compliance (Sheet 1)
        self.core_checks = {
            'mit_planning': MITPlanningCheck(self.criteria_config),
            'mit_creation': MITCreationCheck(self.criteria_config),
            'mit_completion': MITCompletionCheck(self.criteria_config),
            'non_mit_tracking': NonMITTrackingCheck(self.criteria_config),
            'recap_to_jira_conversion': RecapToJiraConversionCheck(self.criteria_config),
            'status_hygiene': StatusHygieneCheck(),
            'task_cancellation': CancellationCheck(),
            'weekly_updates': UpdateFrequencyCheck(),
            'roles_and_access': RoleOwnershipCheck(),
            'documentation_traceability': DocumentationCheck(),
            'lifecycle_adherence': LifecycleCheck(),
        }
        
        # Manual compliance (Sheet 2)
        self.manual_checks = {
            'comment_quality': CommentQualityCheck(self.criteria_config),
            'missing_comments': MissingCommentsCheck(self.criteria_config),
            'screenshot_only_evidence': ScreenshotOnlyEvidenceCheck(self.criteria_config),
            'doc_link_only_evidence': DocLinkOnlyEvidenceCheck(self.criteria_config),
            'description_quality': DescriptionQualityCheck(self.criteria_config),
            'title_quality': TitleQualityCheck(self.criteria_config),
            'multiple_issues_in_one_ticket': MultipleIssuesCheck(self.criteria_config),
            'history_integrity': HistoryIntegrityCheck(self.criteria_config),
            'acceptance_criteria_relevance': AcceptanceCriteriaRelevanceCheck(self.criteria_config),
            'productivity_validity': ProductivityValidityCheck(self.criteria_config),
            'evidence_relevance': EvidenceRelevanceCheck(self.criteria_config),
        }
        
        # Combined all checks
        self.all_checks = {**self.core_checks, **self.manual_checks}
    
    def generate_audit_report(
        self,
        ticket_keys: List[str],
        output_format: str = "markdown"
    ) -> str:
        """
        Generate detailed compliance audit report for specific tickets.
        
        Args:
            ticket_keys: List of Jira issue keys to audit
            output_format: Output format (markdown, json, excel)
            
        Returns:
            Path to generated report file
        """
        logger.info(f"Generating audit report for {len(ticket_keys)} tickets")
        
        # Fetch all ticket data
        tickets_data = self._fetch_tickets_data(ticket_keys)
        
        # Evaluate each ticket
        audit_results = []
        for ticket in tickets_data:
            result = self._evaluate_ticket(ticket)
            audit_results.append(result)
        
        # Generate executive summary
        summary = self._generate_executive_summary(audit_results)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(audit_results)
        
        # Format and save report
        if output_format == "markdown":
            report_path = self._save_markdown_report(summary, audit_results, recommendations)
        elif output_format == "json":
            report_path = self._save_json_report(summary, audit_results, recommendations)
        elif output_format == "excel":
            report_path = self._save_excel_report(summary, audit_results, recommendations)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        logger.info(f"Audit report generated: {report_path}")
        return str(report_path)
    
    def _fetch_tickets_data(self, ticket_keys: List[str]) -> List[Dict]:
        """
        Fetch full ticket data including changelog and comments.
        
        Args:
            ticket_keys: List of issue keys
            
        Returns:
            List of ticket dictionaries with full data
        """
        tickets = []
        for key in ticket_keys:
            try:
                ticket = self.jira_client.get_issue(
                    key,
                    expand='changelog,renderedFields'
                )
                tickets.append(ticket)
                logger.debug(f"Fetched ticket {key}")
            except Exception as e:
                logger.error(f"Failed to fetch ticket {key}: {e}")
                # Add placeholder for failed fetch
                tickets.append({
                    'key': key,
                    'fetch_error': str(e),
                    'fields': {}
                })
        
        return tickets
    
    def _evaluate_ticket(self, ticket: Dict) -> Dict:
        """
        Evaluate a single ticket against all applicable criteria.
        
        Args:
            ticket: Ticket data dictionary
            
        Returns:
            Evaluation result dictionary
        """
        issue_key = ticket.get('key', 'UNKNOWN')
        logger.info(f"Evaluating ticket {issue_key}")
        
        # Check if ticket fetch failed
        if 'fetch_error' in ticket:
            return {
                'issue_key': issue_key,
                'overall_status': 'ERROR',
                'error': ticket['fetch_error'],
                'criteria_results': {},
                'zero_tolerance_violations': []
            }
        
        # Determine if ticket is MIT or Non-MIT
        is_mit = self._is_mit_ticket(ticket)
        
        # Evaluate applicable checks
        criteria_results = {}
        zero_tolerance_violations = []
        stop_evaluation = False
        
        # Evaluate core checks
        for check_id, check in self.core_checks.items():
            # Skip MIT-specific checks for non-MIT tickets
            if check_id in ['mit_planning', 'mit_creation', 'mit_completion'] and not is_mit:
                criteria_results[check_id] = {'status': 'NA', 'reason': 'Not a MIT ticket'}
                continue
            
            # Skip non-MIT checks for MIT tickets
            if check_id == 'non_mit_tracking' and is_mit:
                criteria_results[check_id] = {'status': 'NA', 'reason': 'MIT ticket'}
                continue
            
            # Evaluate check
            if not stop_evaluation:
                result = check.evaluate([ticket], None)
                criteria_results[check_id] = result
                
                # Check for zero-tolerance violation
                if result.get('zero_tolerance') and result['status'] == 'Fail':
                    zero_tolerance_violations.append({
                        'criterion': check_id,
                        'reason': result.get('reason', 'Zero tolerance violation')
                    })
                    stop_evaluation = self.criteria_config['settings']['zero_tolerance_stops_evaluation']
        
        # Evaluate manual checks (unless stopped)
        if not stop_evaluation:
            for check_id, check in self.manual_checks.items():
                result = check.evaluate([ticket], None)
                criteria_results[check_id] = result
                
                # Check for zero-tolerance violation
                if result.get('zero_tolerance') and result['status'] == 'Fail':
                    zero_tolerance_violations.append({
                        'criterion': check_id,
                        'reason': result.get('reason', 'Zero tolerance violation')
                    })
                    stop_evaluation = self.criteria_config['settings']['zero_tolerance_stops_evaluation']
        
        # Calculate overall status
        overall_status = self._calculate_overall_status(criteria_results, zero_tolerance_violations)
        
        return {
            'issue_key': issue_key,
            'overall_status': overall_status,
            'is_mit': is_mit,
            'criteria_results': criteria_results,
            'zero_tolerance_violations': zero_tolerance_violations,
            'ticket_summary': ticket.get('fields', {}).get('summary', ''),
            'ticket_status': ticket.get('fields', {}).get('status', {}).get('name', 'Unknown')
        }
    
    def _is_mit_ticket(self, ticket: Dict) -> bool:
        """
        Determine if ticket is a MIT (Most Important Task).
        
        Args:
            ticket: Ticket data
            
        Returns:
            True if MIT, False otherwise
        """
        mit_config = self.criteria_config['settings']['mit_identification']
        method = mit_config['method']
        
        fields = ticket.get('fields', {})
        
        if method == 'label':
            labels = fields.get('labels', [])
            return mit_config['label_name'] in labels
        elif method == 'custom_field':
            custom_field = fields.get(mit_config['custom_field_id'])
            return custom_field is not None and custom_field == True
        elif method == 'issue_type':
            issue_type = fields.get('issuetype', {}).get('name', '')
            return issue_type == mit_config['issue_type_name']
        elif method == 'naming_pattern':
            summary = fields.get('summary', '')
            return mit_config['naming_pattern'] in summary.upper()
        
        return False
    
    def _calculate_overall_status(
        self,
        criteria_results: Dict,
        zero_tolerance_violations: List[Dict]
    ) -> str:
        """
        Calculate overall compliance status for ticket.
        
        Args:
            criteria_results: All criteria evaluation results
            zero_tolerance_violations: List of zero-tolerance violations
            
        Returns:
            Overall status: COMPLIANT, NON-COMPLIANT, or ZERO_TOLERANCE_FAIL
        """
        if zero_tolerance_violations:
            return "ZERO_TOLERANCE_FAIL"
        
        # Check if any criterion failed
        for criterion, result in criteria_results.items():
            if isinstance(result, dict) and result.get('status') == 'Fail':
                return "NON-COMPLIANT"
        
        return "COMPLIANT"
    
    def _generate_executive_summary(self, audit_results: List[Dict]) -> Dict:
        """Generate executive summary statistics."""
        total = len(audit_results)
        compliant = sum(1 for r in audit_results if r['overall_status'] == 'COMPLIANT')
        non_compliant = sum(1 for r in audit_results if r['overall_status'] == 'NON-COMPLIANT')
        zero_tolerance_fails = sum(1 for r in audit_results if r['overall_status'] == 'ZERO_TOLERANCE_FAIL')
        
        # Collect zero-tolerance violations
        zt_violations = {}
        for result in audit_results:
            for violation in result.get('zero_tolerance_violations', []):
                criterion = violation['criterion']
                if criterion not in zt_violations:
                    zt_violations[criterion] = []
                zt_violations[criterion].append(result['issue_key'])
        
        return {
            'total_audited': total,
            'compliant_count': compliant,
            'non_compliant_count': non_compliant,
            'zero_tolerance_count': zero_tolerance_fails,
            'compliance_rate': (compliant / total * 100) if total > 0 else 0,
            'zero_tolerance_violations': zt_violations
        }
    
    def _generate_recommendations(self, audit_results: List[Dict]) -> List[Dict]:
        """
        Generate actionable recommendations grouped by failure type.
        
        Args:
            audit_results: All ticket audit results
            
        Returns:
            List of recommendation dictionaries
        """
        # Group failures by criterion
        failure_counts = {}
        failure_examples = {}
        
        for result in audit_results:
            for criterion, check_result in result.get('criteria_results', {}).items():
                if isinstance(check_result, dict) and check_result.get('status') == 'Fail':
                    if criterion not in failure_counts:
                        failure_counts[criterion] = 0
                        failure_examples[criterion] = []
                    failure_counts[criterion] += 1
                    failure_examples[criterion].append({
                        'issue_key': result['issue_key'],
                        'reason': check_result.get('reason', 'N/A')
                    })
        
        # Sort by frequency
        sorted_failures = sorted(failure_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Generate recommendations
        recommendations = []
        for criterion, count in sorted_failures:
            # Get criterion info from config
            criterion_info = self._get_criterion_info(criterion)
            
            is_zero_tolerance = criterion_info.get('zero_tolerance', False)
            
            recommendations.append({
                'criterion': criterion,
                'category': criterion_info.get('category', criterion),
                'failed_count': count,
                'zero_tolerance': is_zero_tolerance,
                'issue': criterion_info.get('failure_looks_like', ''),
                'fix': self._generate_fix_suggestion(criterion, criterion_info),
                'priority': 'CRITICAL' if is_zero_tolerance else ('HIGH' if count > 3 else 'MEDIUM'),
                'examples': failure_examples[criterion][:3]  # Top 3 examples
            })
        
        return recommendations
    
    def _get_criterion_info(self, criterion_id: str) -> Dict:
        """Get criterion configuration info."""
        # Check core compliance
        if criterion_id in self.criteria_config.get('core_process_compliance', {}):
            return self.criteria_config['core_process_compliance'][criterion_id]
        # Check manual compliance
        if criterion_id in self.criteria_config.get('manual_compliance', {}):
            return self.criteria_config['manual_compliance'][criterion_id]
        return {}
    
    def _generate_fix_suggestion(self, criterion_id: str, criterion_info: Dict) -> str:
        """Generate actionable fix suggestion for a criterion."""
        fixes = {
            'task_cancellation': "Require manager approval comment within 24 hours of setting status to 'Cancelled'. Add Jira automation to block cancellation status unless approval keyword is present.",
            'comment_quality': "Enforce comment templates requiring: context, progress made, decisions, or blockers. Minimum 10 words.",
            'description_quality': "Use Jira description template requiring: What (problem statement), Why (business value), How (approach). Minimum 50 characters.",
            'title_quality': "Enforce title guidelines: specific, descriptive, 10-100 characters. Avoid generic terms.",
            'mit_planning': "Ensure 3-5 MITs are proposed and approved by Monday EOD each week. Use recurring calendar reminder.",
            'history_integrity': "Disable bulk status updates. Flag retroactive changes (>24h after original transition) for manager review.",
        }
        
        return fixes.get(criterion_id, criterion_info.get('success_looks_like', 'Follow best practices'))
    
    def _save_markdown_report(
        self,
        summary: Dict,
        audit_results: List[Dict],
       recommendations: List[Dict]
    ) -> Path:
        """Save audit report as markdown file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"JIRA_Compliance_Audit_{timestamp}.md"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # Write header
            f.write("# JIRA COMPLIANCE AUDIT REPORT\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            # Executive Summary
            f.write("## A. Executive Summary\n\n")
            f.write(f"- **Total Tickets Audited:** {summary['total_audited']}\n")
            f.write(f"- **Fully Compliant:** {summary['compliant_count']} ({summary['compliant_count']/summary['total_audited']*100:.1f}%)\n")
            f.write(f"- **Non-Compliant:** {summary['non_compliant_count']} ({summary['non_compliant_count']/summary['total_audited']*100:.1f}%)\n")
            f.write(f"- **Zero-Tolerance Violations:** {summary['zero_tolerance_count']} ({summary['zero_tolerance_count']/summary['total_audited']*100:.1f}%)\n")
            
            if summary['zero_tolerance_violations']:
                f.write("\n**Zero-Tolerance Violations by Criterion:**\n")
                for criterion, tickets in summary['zero_tolerance_violations'].items():
                    criterion_info = self._get_criterion_info(criterion)
                    f.write(f"  - **{criterion_info.get('category', criterion)}:** {', '.join(tickets)}\n")
            
            f.write(f"\n- **Overall Compliance Rate:** {summary['compliance_rate']:.1f}%\n\n")
            f.write("---\n\n")
            
            # Detailed Breakdown
            f.write("## B. Detailed Ticket-by-Ticket Breakdown\n\n")
            
            for result in audit_results:
                self._write_ticket_breakdown(f, result)
            
            # Recommendations
            f.write("## C. Recommendations\n\n")
            
            for i, rec in enumerate(recommendations, 1):
                f.write(f"### {i}. {rec['category']} ({rec['failed_count']} tickets FAILED")
                if rec['zero_tolerance']:
                    f.write(" - **Zero Tolerance**")
                f.write(")\n\n")
                
                f.write(f"**Issue:** {rec['issue']}\n\n")
                f.write(f"**Actionable Fix:**\n{rec['fix']}\n\n")
                f.write(f"**Priority:** {rec['priority']}\n\n")
                
                if rec['examples']:
                    f.write("**Example Failures:**\n")
                    for ex in rec['examples']:
                        f.write(f"- `{ex['issue_key']}`: {ex['reason']}\n")
                f.write("\n---\n\n")
        
        return filepath
    
    def _write_ticket_breakdown(self, f, result: Dict):
        """Write ticket breakdown section to markdown file."""
        f.write(f"### Ticket: {result['issue_key']}\n\n")
        f.write(f"**Summary:** {result.get('ticket_summary', 'N/A')}\n\n")
        f.write(f"**Overall Status:** ")
        
        if result['overall_status'] == 'COMPLIANT':
            f.write("✅ **COMPLIANT**\n\n")
        elif result['overall_status'] == 'NON-COMPLIANT':
            f.write("❌ **NON-COMPLIANT**\n\n")
        else:
            f.write("🚫 **ZERO TOLERANCE FAIL**\n\n")
        
        # Criteria table
        f.write("| Criterion | Pass/Fail | Remarks |\n")
        f.write("|-----------|-----------|----------|\n")
        
        for criterion_id, check_result in result.get('criteria_results', {}).items():
            criterion_info = self._get_criterion_info(criterion_id)
            category = criterion_info.get('category', criterion_id)
            
            if isinstance(check_result, dict):
                status = check_result.get('status', 'Unknown')
                reason = check_result.get('reason', 'N/A')
                
                if status == 'Pass':
                    symbol = "✓"
                elif status == 'Fail':
                    symbol = "✗"
                else:
                    symbol = "—"
                
                f.write(f"| {category} | {symbol} | {reason} |\n")
        
        # Zero tolerance violation note
        f.write(f"\n**Zero Tolerance Violated?** ")
        if result.get('zero_tolerance_violations'):
            violations = ', '.join([v['criterion'] for v in result['zero_tolerance_violations']])
            f.write(f"**YES** - {violations}\n\n")
        else:
            f.write("No\n\n")
        
        f.write("---\n\n")
    
    def _save_json_report(self, summary: Dict, audit_results: List[Dict], recommendations: List[Dict]) -> Path:
        """Save audit report as JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"JIRA_Compliance_Audit_{timestamp}.json"
        filepath = self.output_dir / filename
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'executive_summary': summary,
            'audit_results': audit_results,
            'recommendations': recommendations
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def _save_excel_report(self, summary: Dict, audit_results: List[Dict], recommendations: List[Dict]) -> Path:
        """Save audit report as Excel file (to be implemented)."""
        # TODO: Implement Excel export
        raise NotImplementedError("Excel export not yet implemented. Use markdown or JSON format.")
