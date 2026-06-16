# -*- coding: utf-8 -*-
"""
DrawAnywhere GUI Automation - Test Report Generator
=====================================================
Generates comprehensive test reports in multiple formats:
- Console summary output
- HTML report with styling
- JSON data export
- Screenshot references

Usage:
    from report import TestReport
    report = TestReport()
    report.add_result(test_case_result)
    report.generate_html("report.html")
    report.print_summary()
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from base_test import TestCaseResult, TestStepResult
from config import REPORT_DIR, REPORT_TITLE, REPORT_DESCRIPTION

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Report Data Classes
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class TestSuiteResult:
    """Aggregated results for the entire test suite."""
    title: str = REPORT_TITLE
    description: str = REPORT_DESCRIPTION
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    total_steps: int = 0
    passed_steps: int = 0
    failed_steps: int = 0
    total_duration_ms: float = 0.0
    results: List[TestCaseResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100

    @property
    def step_pass_rate(self) -> float:
        if self.total_steps == 0:
            return 0.0
        return (self.passed_steps / self.total_steps) * 100


# ────────────────────────────────────────────────────────────────────────────
# Report Generator
# ────────────────────────────────────────────────────────────────────────────

class TestReport:
    """
    Generates test reports in multiple formats.

    Usage:
        report = TestReport()
        report.add_result(result1)
        report.add_result(result2)
        report.print_console_summary()
        report.generate_html("report.html")
        report.generate_json("results.json")
    """

    def __init__(self, title: str = REPORT_TITLE, description: str = REPORT_DESCRIPTION):
        self.suite = TestSuiteResult(title=title, description=description)

    def add_result(self, result: TestCaseResult):
        """Add a single test case result to the report."""
        self.suite.results.append(result)
        self.suite.total_tests += 1
        self.suite.total_steps += len(result.steps)

        if result.passed:
            self.suite.passed_tests += 1
        else:
            self.suite.failed_tests += 1

        self.suite.passed_steps += sum(1 for s in result.steps if s.passed)
        self.suite.failed_steps += sum(1 for s in result.steps if not s.passed)
        self.suite.total_duration_ms += result.duration_ms

    def finalize(self):
        """Mark suite as complete."""
        self.suite.end_time = datetime.now()

    # ── Console Summary ───────────────────────────────────────────────────

    def print_console_summary(self):
        """Print a formatted summary to console."""
        self.finalize()

        print()
        print("=" * 70)
        print(f"  {self.suite.title}")
        print(f"  {self.suite.description}")
        print("=" * 70)
        print(f"  Start:     {self.suite.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  End:       {self.suite.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.suite.end_time else 'N/A'}")
        print(f"  Duration:  {self.suite.total_duration_ms / 1000:.2f}s")
        print("-" * 70)
        print(f"  Tests:     {self.suite.total_tests} total")
        print(f"             {self.suite.passed_tests} passed  ✓")
        print(f"             {self.suite.failed_tests} failed  ✗")
        print(f"  Pass Rate: {self.suite.pass_rate:.1f}%")
        print(f"  Steps:     {self.suite.total_steps} total")
        print(f"             {self.suite.passed_steps} passed")
        print(f"             {self.suite.failed_steps} failed")
        print(f"  Step Rate: {self.suite.step_pass_rate:.1f}%")
        print("-" * 70)

        # Per-module breakdown
        modules: Dict[str, List[TestCaseResult]] = {}
        for r in self.suite.results:
            modules.setdefault(r.module, []).append(r)

        for module_name, module_results in modules.items():
            passed = sum(1 for r in module_results if r.passed)
            failed = sum(1 for r in module_results if not r.passed)
            status = "✓" if failed == 0 else "✗"
            print(f"  [{status}] {module_name}: {passed}/{len(module_results)} passed")

        # Failed test details
        if self.suite.failed_tests > 0:
            print("-" * 70)
            print("  FAILED TESTS:")
            for r in self.suite.results:
                if not r.passed:
                    print(f"    ✗ [{r.module}] {r.name}")
                    if r.error:
                        print(f"      Error: {r.error}")
                    for step in r.steps:
                        if not step.passed:
                            print(f"      └─ Step '{step.name}' FAILED: {step.error}")

        print("=" * 70)
        print()

    # ── HTML Report ───────────────────────────────────────────────────────

    def generate_html(self, filepath: Optional[Path] = None) -> Path:
        """
        Generate an HTML test report.

        Args:
            filepath: Output path. Default: REPORT_DIR/test_report_<timestamp>.html

        Returns:
            Path to the generated report.
        """
        self.finalize()

        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = REPORT_DIR / f"test_report_{timestamp}.html"
        else:
            filepath = Path(filepath)

        html = self._build_html()
        filepath.write_text(html, encoding="utf-8")
        logger.info("HTML report generated: %s", filepath)
        return filepath

    def _build_html(self) -> str:
        """Build the HTML report content."""
        s = self.suite
        passed_color = "#28a745"
        failed_color = "#dc3545"
        warn_color = "#ffc107"

        rows_html = ""
        for r in s.results:
            status_icon = "✅" if r.passed else "❌"
            status_class = "passed" if r.passed else "failed"
            status_color = passed_color if r.passed else failed_color

            steps_html = ""
            for step in r.steps:
                step_icon = "✅" if step.passed else "❌"
                step_class = "passed" if step.passed else "failed"
                error_html = ""
                if step.error:
                    error_html = f'<span class="error-msg">{step.error}</span>'
                steps_html += f"""
                <tr class="step-row {step_class}">
                    <td style="padding-left: 24px;">{step_icon}</td>
                    <td>{step.name}</td>
                    <td>{step_icon} {step_class.upper()}</td>
                    <td>{step.duration_ms:.0f}ms</td>
                    <td>{error_html}</td>
                </tr>"""

            error_section = ""
            if r.error and not r.passed:
                error_section = f'<div class="error-box">❌ {r.error}</div>'

            rows_html += f"""
            <tr class="test-row {status_class}">
                <td>{status_icon}</td>
                <td><strong>{r.module}</strong></td>
                <td>{r.name}</td>
                <td style="color:{status_color}; font-weight:bold;">{status_class.upper()}</td>
                <td>{r.duration_ms:.0f}ms</td>
            </tr>
            <tr class="error-detail" style="display:none;">
                <td colspan="5">{error_section}
                    <table class="steps-table">
                        <thead><tr><th></th><th>Step</th><th>Result</th><th>Duration</th><th>Error</th></tr></thead>
                        <tbody>{steps_html}</tbody>
                    </table>
                </td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{s.title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: #f5f5f5; color: #333; padding: 20px; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                  color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .header p {{ opacity: 0.9; font-size: 14px; }}
        .summary {{ display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }}
        .summary-card {{ background: white; border-radius: 10px; padding: 20px; flex: 1;
                        min-width: 140px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }}
        .summary-card .value {{ font-size: 32px; font-weight: bold; margin: 8px 0; }}
        .summary-card .label {{ font-size: 12px; color: #888; text-transform: uppercase; }}
        .summary-card.pass {{ border-top: 4px solid {passed_color}; }}
        .summary-card.fail {{ border-top: 4px solid {failed_color}; }}
        .summary-card.info {{ border-top: 4px solid #17a2b8; }}
        table {{ width: 100%; border-collapse: collapse; background: white;
                border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        th {{ background: #f8f9fa; padding: 12px 16px; text-align: left; font-size: 13px;
             text-transform: uppercase; color: #888; border-bottom: 2px solid #e9ecef; }}
        td {{ padding: 10px 16px; border-bottom: 1px solid #e9ecef; font-size: 14px; }}
        tr:hover {{ background: #f8f9fa; }}
        .passed {{  }}
        .failed {{ background: #fff5f5; }}
        .error-box {{ background: #fff5f5; border: 1px solid {failed_color};
                     border-radius: 6px; padding: 12px; margin: 8px 0; color: {failed_color}; }}
        .error-msg {{ color: {failed_color}; font-size: 12px; margin-left: 8px; }}
        .steps-table {{ margin-top: 8px; font-size: 13px; }}
        .steps-table th {{ font-size: 11px; padding: 6px 12px; }}
        .steps-table td {{ padding: 6px 12px; }}
        .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
    </style>
    <script>
        // Make test rows expandable to show step details
        document.addEventListener('DOMContentLoaded', function() {{
            document.querySelectorAll('.test-row').forEach(function(row) {{
                row.style.cursor = 'pointer';
                row.addEventListener('click', function() {{
                    var detail = row.nextElementSibling;
                    if (detail && detail.classList.contains('error-detail')) {{
                        detail.style.display = detail.style.display === 'none' ? 'table-row' : 'none';
                    }}
                }});
            }});
        }});
    </script>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>{s.title}</h1>
        <p>{s.description}</p>
        <p>Generated: {s.end_time.strftime('%Y-%m-%d %H:%M:%S') if s.end_time else 'N/A'}</p>
    </div>

    <div class="summary">
        <div class="summary-card {'pass' if s.failed_tests == 0 else 'fail'}">
            <div class="label">Tests</div>
            <div class="value">{s.passed_tests}/{s.total_tests}</div>
            <div class="label">Pass Rate: {s.pass_rate:.1f}%</div>
        </div>
        <div class="summary-card {'fail' if s.failed_steps > 0 else 'pass'}">
            <div class="label">Steps</div>
            <div class="value">{s.passed_steps}/{s.total_steps}</div>
            <div class="label">Step Rate: {s.step_pass_rate:.1f}%</div>
        </div>
        <div class="summary-card info">
            <div class="label">Duration</div>
            <div class="value">{s.total_duration_ms / 1000:.1f}s</div>
            <div class="label">Total Time</div>
        </div>
        <div class="summary-card {'pass' if s.failed_tests == 0 else 'fail'}">
            <div class="label">Status</div>
            <div class="value">{'PASS' if s.failed_tests == 0 else 'FAIL'}</div>
            <div class="label">{s.total_tests} test(s)</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th width="30"></th>
                <th>Module</th>
                <th>Test Name</th>
                <th>Result</th>
                <th>Duration</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>

    <div class="footer">
        DrawAnywhere UIAutomator2 Test Report · Generated by test_runner.py
    </div>
</div>
</body>
</html>"""
        return html

    # ── JSON Report ───────────────────────────────────────────────────────

    def generate_json(self, filepath: Optional[Path] = None) -> Path:
        """
        Generate a JSON test report.

        Args:
            filepath: Output path. Default: REPORT_DIR/test_results_<timestamp>.json

        Returns:
            Path to the generated report.
        """
        self.finalize()

        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = REPORT_DIR / f"test_results_{timestamp}.json"
        else:
            filepath = Path(filepath)

        data = {
            "title": self.suite.title,
            "description": self.suite.description,
            "start_time": self.suite.start_time.isoformat(),
            "end_time": self.suite.end_time.isoformat() if self.suite.end_time else None,
            "summary": {
                "total_tests": self.suite.total_tests,
                "passed_tests": self.suite.passed_tests,
                "failed_tests": self.suite.failed_tests,
                "pass_rate": round(self.suite.pass_rate, 2),
                "total_steps": self.suite.total_steps,
                "passed_steps": self.suite.passed_steps,
                "failed_steps": self.suite.failed_steps,
                "step_pass_rate": round(self.suite.step_pass_rate, 2),
                "total_duration_ms": self.suite.total_duration_ms,
            },
            "test_cases": [],
        }

        for r in self.suite.results:
            case = {
                "module": r.module,
                "name": r.name,
                "passed": r.passed,
                "duration_ms": r.duration_ms,
                "error": r.error,
                "steps": [],
            }
            for step in r.steps:
                case["steps"].append({
                    "name": step.name,
                    "passed": step.passed,
                    "duration_ms": step.duration_ms,
                    "error": step.error,
                })
            data["test_cases"].append(case)

        filepath.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        logger.info("JSON report generated: %s", filepath)
        return filepath
