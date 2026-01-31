#!/usr/bin/env python
"""
Quick Verification Script for Compliance Reporting System
Verifies that all modules can be imported and basic functionality works.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    print("=" * 70)
    print("JIRA Compliance Report System - Quick Verification")
    print("=" * 70)
    print()
    
    results = []
    
    # Test 1: Import compliance checks
    print("1. Testing compliance check imports...")
    try:
        from src.compliance.checks import (
            StatusHygieneCheck,
            CancellationCheck,
            UpdateFrequencyCheck,
            RoleOwnershipCheck,
            DocumentationCheck,
            LifecycleCheck,
            ZeroToleranceCheck
        )
        print("   ✅ All 7 compliance checks imported successfully")
        results.append(True)
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        results.append(False)
    print()
    
    # Test 2: Import report builder
    print("2. Testing report builder import...")
    try:
        from src.reports.compliance_builder import ComplianceReportBuilder
        print("   ✅ ComplianceReportBuilder imported successfully")
        results.append(True)
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        results.append(False)
    print()
    
    # Test 3: Check demo script
    print("3. Verifying demo script exists...")
    demo_script = Path(__file__).parent / "demo_compliance_report.py"
    if demo_script.exists():
        print(f"   ✅ Demo script found: {demo_script.name}")
        results.append(True)
    else:
        print(f"   ❌ Demo script not found")
        results.append(False)
    print()
    
    # Test 4: Check CLI script
    print("4. Verifying CLI script exists...")
    cli_script = Path(__file__).parent / "generate_compliance_report.py"
    if cli_script.exists():
        print(f"   ✅ CLI script found: {cli_script.name}")
        results.append(True)
    else:
        print(f"   ❌ CLI script not found")
        results.append(False)
    print()
    
    # Test 5: Check config file
    print("5. Verifying compliance rules config...")
    config_file = Path(__file__).parent.parent / "config" / "compliance_rules.yaml"
    if config_file.exists():
        print(f"   ✅ Configuration file found: {config_file.name}")
        results.append(True)
    else:
        print(f"   ⚠️  Configuration file not found (optional)")
        results.append(True)  # Not critical
    print()
    
    # Test 6: Check output directory
    print("6. Verifying output directory...")
    output_dir = Path(__file__).parent.parent / "outputs"
    if output_dir.exists():
        xlsx_files = list(output_dir.glob("*.xlsx"))
        print(f"   ✅ Output directory exists")
        print(f"   📊 Found {len(xlsx_files)} Excel report(s)")
        results.append(True)
    else:
        print(f"   ⚠️  Output directory not found (will be created on first run)")
        results.append(True)  # Not critical
    print()
    
    # Test 7: Test basic compliance check instantiation
    print("7. Testing compliance check instantiation...")
    try:
        from src.compliance.checks import StatusHygieneCheck
        check = StatusHygieneCheck()
        print(f"   ✅ StatusHygieneCheck created successfully")
        print(f"   📋 Valid transitions defined: {len(check.VALID_TRANSITIONS)} statuses")
        results.append(True)
    except Exception as e:
        print(f"   ❌ Instantiation failed: {e}")
        results.append(False)
    print()
    
    # Test 8: Check unit tests exist
    print("8. Verifying unit tests...")
    test_file = Path(__file__).parent.parent / "tests" / "test_compliance_checks.py"
    if test_file.exists():
        # Count test methods
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
            test_count = content.count("def test_")
        print(f"   ✅ Unit test file found")
        print(f"   🧪 Contains {test_count} test cases")
        results.append(True)
    else:
        print(f"   ❌ Unit test file not found")
        results.append(False)
    print()
    
    # Summary
    print("=" * 70)
    print("Verification Summary")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Checks Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    print()
    
    if passed == total:
        print("🎉 All verifications passed! System is ready to use.")
        print()
        print("Next steps:")
        print("  1. Run demo: python scripts/demo_compliance_report.py")
        print("  2. Or generate real report: python scripts/generate_compliance_report.py")
        return 0
    else:
        print("⚠️  Some verifications failed. Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
