#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DrawAnywhere GUI Automation - Test Runner
===========================================
Main entry point for executing all GUI automation tests.

Usage:
    # Run all tests:
    python test_runner.py

    # Run specific module(s):
    python test_runner.py --modules launch drawing

    # Run with verbose output:
    python test_runner.py --verbose

    # Set device serial:
    python test_runner.py --device 127.0.0.1:5555

    # Generate only HTML report:
    python test_runner.py --report html

    # Clean start (force stop app first):
    python test_runner.py --clean

Dependencies:
    - uiautomator2
    - Python 3.8+
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type

# Ensure tests/ is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uiautomator2 as u2

from config import (
    DEVICE_SERIAL,
    PACKAGE_NAME,
    LOG_LEVEL,
    SCREENSHOT_DIR,
    REPORT_DIR,
    LOG_DIR,
)
from base_test import BaseTest, TestCaseResult
from report import TestReport

# Import all test modules
from test_launch import TestAppLaunch, TestAppReLaunch
from test_drawing import TestDrawingOperations

logger = logging.getLogger("runner")


# ────────────────────────────────────────────────────────────────────────────
# Test Registry
# ────────────────────────────────────────────────────────────────────────────

# Maps module names to their test classes
TEST_REGISTRY: Dict[str, List[Type[BaseTest]]] = {
    "launch":   [TestAppLaunch, TestAppReLaunch],
    "drawing":  [TestDrawingOperations],
}

ALL_MODULES = list(TEST_REGISTRY.keys())

# Execution order (important: launch first)
EXECUTION_ORDER = ["launch", "drawing"]


# ────────────────────────────────────────────────────────────────────────────
# Test Runner
# ────────────────────────────────────────────────────────────────────────────

class TestRunner:
    """
    Orchestrates test execution, collects results, and generates reports.

    Usage:
        runner = TestRunner(modules=["launch", "drawing"], verbose=True)
        runner.run_all()
        runner.generate_reports()
    """

    def __init__(
        self,
        modules: Optional[List[str]] = None,
        verbose: bool = False,
        device_serial: Optional[str] = None,
        clean_start: bool = False,
    ):
        self.modules = modules or ALL_MODULES
        self.verbose = verbose
        self.device_serial = device_serial or DEVICE_SERIAL
        self.clean_start = clean_start
        self.report = TestReport()
        self.device: Optional[u2.Device] = None
        self.start_time: Optional[datetime] = None

        # Validate modules
        for m in self.modules:
            if m not in TEST_REGISTRY:
                logger.error("Unknown module: '%s'. Available: %s", m, ALL_MODULES)
                sys.exit(1)

        # Sort by execution order
        self.modules.sort(key=lambda m: EXECUTION_ORDER.index(m) if m in EXECUTION_ORDER else 99)

    # ── Main Entry Point ──────────────────────────────────────────────────

    def run_all(self) -> bool:
        """
        Run all selected test modules.

        Returns:
            True if all tests passed, False otherwise.
        """
        self.start_time = datetime.now()

        print()
        print("╔" + "═" * 68 + "╗")
        print("║  DrawAnywhere GUI Automation Test Suite                       ║")
        print("║  Framework: UIAutomator2                                      ║")
        print(f"║  Started:   {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}                        ║")
        print("╚" + "═" * 68 + "╝")
        print()

        # ── Connect to device ────────────────────────────────────────────
        try:
            if self.device_serial:
                self.device = u2.connect(self.device_serial)
                logger.info("Connected to device: %s", self.device_serial)
            else:
                self.device = u2.connect()
                logger.info("Connected to device (auto-detect)")
        except Exception as e:
            logger.error("Failed to connect to device: %s", e)
            logger.error(
                "Make sure:"
                "\n  1. Device is connected via USB with USB debugging enabled"
                "\n  2. adb devices shows the device"
                "\n  3. uiautomator2 is installed (python -m uiautomator2 init)"
            )
            return False

        # Show device info
        try:
            info = self.device.info
            print(f"  Device: {info.get('product', 'unknown')} "
                  f"(SDK {info.get('sdkInt', '?')}, "
                  f"{info.get('displayWidth', '?')}x{info.get('displayHeight', '?')})")
            print()
        except Exception:
            pass

        # ── Clean start if requested ─────────────────────────────────────
        if self.clean_start:
            logger.info("Clean start: stopping app...")
            try:
                self.device.app_stop(PACKAGE_NAME)
                time.sleep(1)
            except Exception:
                pass

        # ── Run test modules ─────────────────────────────────────────────
        all_passed = True
        for module_name in self.modules:
            test_classes = TEST_REGISTRY[module_name]

            for test_cls in test_classes:
                print(f"  ▶ Running [{module_name}] {test_cls.TEST_NAME}...")
                try:
                    test_instance = test_cls()
                    result = test_instance.run()
                    self.report.add_result(result)

                    status = "✓ PASSED" if result.passed else "✗ FAILED"
                    print(f"    {status} ({result.duration_ms:.0f}ms, "
                          f"{sum(1 for s in result.steps if s.passed)}/{len(result.steps)} steps)")
                    if not result.passed:
                        all_passed = False
                        if result.error:
                            print(f"    Error: {result.error}")

                except Exception as e:
                    logger.error("Test [%s] %s crashed: %s", module_name, test_cls.TEST_NAME, e)
                    logger.debug(traceback.format_exc())
                    all_passed = False
                    # Create a synthetic failure result
                    from base_test import TestCaseResult
                    crash_result = TestCaseResult(
                        name=test_cls.TEST_NAME,
                        module=module_name,
                        passed=False,
                        error=f"CRASH: {type(e).__name__}: {e}",
                    )
                    self.report.add_result(crash_result)
                    print(f"    ✗ CRASHED: {e}")

                print()

        # ── Generate reports ─────────────────────────────────────────────
        self.generate_reports()

        return all_passed

    # ── Report Generation ─────────────────────────────────────────────────

    def generate_reports(self):
        """Generate all report formats."""
        print("-" * 70)
        print("  Generating reports...")

        # Console summary
        self.report.print_console_summary()

        # HTML report
        html_path = self.report.generate_html()
        print(f"  HTML report: {html_path}")

        # JSON report
        json_path = self.report.generate_json()
        print(f"  JSON report: {json_path}")

        print()


# ────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ────────────────────────────────────────────────────────────────────────────

def main():
    """Parse command line arguments and run tests."""
    parser = argparse.ArgumentParser(
        description="DrawAnywhere GUI Automation Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_runner.py                              # Run all tests
  python test_runner.py --modules launch drawing     # Run specific modules
  python test_runner.py --verbose                    # Verbose output
  python test_runner.py --device 127.0.0.1:5555      # Connect to specific device
  python test_runner.py --clean                      # Force stop app before tests
  python test_runner.py --modules launch --verbose   # Combine options
        """,
    )

    parser.add_argument(
        "--modules", "-m",
        nargs="+",
        choices=ALL_MODULES,
        default=None,
        help=f"Test modules to run (default: all). Available: {', '.join(ALL_MODULES)}",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging output",
    )
    parser.add_argument(
        "--device", "-d",
        type=str,
        default=None,
        help="Device serial or IP:port (default: auto-detect)",
    )
    parser.add_argument(
        "--clean", "-c",
        action="store_true",
        help="Force stop app before running tests",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available test modules and exit",
    )

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # List modules
    if args.list:
        print("\nAvailable test modules:")
        for mod_name, test_classes in TEST_REGISTRY.items():
            print(f"  [{mod_name}]")
            for tc in test_classes:
                print(f"    - {tc.TEST_NAME}")
        print()
        sys.exit(0)

    # Run tests
    runner = TestRunner(
        modules=args.modules,
        verbose=args.verbose,
        device_serial=args.device,
        clean_start=args.clean,
    )

    all_passed = runner.run_all()

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
