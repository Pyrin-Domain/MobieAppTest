# -*- coding: utf-8 -*-
"""
DrawAnywhere GUI Automation - Base Test Class
===============================================
Provides reusable test infrastructure:
- Device connection setup/teardown
- Automatic screenshot on failure
- Logging configuration
- Common test workflow utilities
- Test metadata tracking

All test modules inherit from this base class.
"""

from __future__ import annotations

import logging
import os
import sys
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import uiautomator2 as u2

# Ensure tests/ is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    DEVICE_SERIAL,
    PACKAGE_NAME,
    DEFAULT_TIMEOUT,
    SHORT_TIMEOUT,
    LONG_TIMEOUT,
    SCREENSHOT_ON_FAILURE,
    SCREENSHOT_ON_STEP,
    SCREENSHOT_DIR,
    SCREENSHOT_FORMAT,
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    LOG_DIR,
    MAX_RETRIES,
    RETRY_DELAY,
    IDLE_TIMEOUT,
    ANIMATION_WAIT,
)
from locator import ElementLocator, create_locator
from actions import UIActions, PopupHandler

# ── Configure Module Logger ─────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            LOG_DIR / f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("test")


# ────────────────────────────────────────────────────────────────────────────
# Test Result Data Classes
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class TestStepResult:
    """Result of a single test step."""
    name: str
    passed: bool
    duration_ms: float
    error: Optional[str] = None
    screenshot: Optional[Path] = None


@dataclass
class TestCaseResult:
    """Result of an entire test case."""
    name: str
    module: str
    passed: bool = False
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    steps: List[TestStepResult] = field(default_factory=list)
    error: Optional[str] = None
    screenshots: List[Path] = field(default_factory=list)


# ────────────────────────────────────────────────────────────────────────────
# Base Test Class
# ────────────────────────────────────────────────────────────────────────────

class BaseTest(ABC):
    """
    Abstract base class for all DrawAnywhere GUI tests.

    Provides:
    - Automatic device connection and cleanup
    - ElementLocator and UIActions instances
    - Screenshot capture on failure
    - Per-step timing and result tracking
    - Logging with test context

    Subclass Usage:
        class MyTest(BaseTest):
            def run_test(self):
                self.step("Launch app", lambda: self.actions.launch_app())
                self.step("Click button", lambda: self.actions.click("visibility"))
                # ... more steps

            # Optionally override:
            def pre_test_setup(self): ...
            def post_test_cleanup(self): ...
    """

    # ── Instance Attributes ───────────────────────────────────────────────

    device: u2.Device
    locator: ElementLocator
    actions: UIActions
    popup_handler: PopupHandler
    result: TestCaseResult
    _current_step_idx: int

    # Subclasses should set these
    TEST_MODULE: str = "base"
    TEST_NAME: str = "unnamed_test"

    def __init__(self):
        self.device = None  # type: ignore[assignment]
        self.locator = None  # type: ignore[assignment]
        self.actions = None  # type: ignore[assignment]
        self.popup_handler = None  # type: ignore[assignment]
        self.result = TestCaseResult(name=self.TEST_NAME, module=self.TEST_MODULE)
        self._current_step_idx = 0

    # ── Lifecycle Methods ─────────────────────────────────────────────────

    def setup(self):
        """
        Initialize device connection and test infrastructure.
        Called once before the test method.
        """
        logger.info("=" * 70)
        logger.info("SETUP: [%s] %s", self.TEST_MODULE, self.TEST_NAME)
        logger.info("=" * 70)

        self.result = TestCaseResult(
            name=self.TEST_NAME,
            module=self.TEST_MODULE,
            start_time=datetime.now(),
        )

        try:
            # Connect to device
            if DEVICE_SERIAL:
                self.device = u2.connect(DEVICE_SERIAL)
                logger.info("Connected to device: %s", DEVICE_SERIAL)
            else:
                self.device = u2.connect()
                serial = self.device.serial if hasattr(self.device, 'serial') else "auto"
                logger.info("Connected to device (auto-detect): %s", serial)

            # Verify connection
            info = self.device.info
            logger.info(
                "Device: %s | SDK: %s | Resolution: %dx%d",
                info.get("product", "unknown"),
                info.get("sdkInt", "unknown"),
                info.get("displayWidth", "?"),
                info.get("displayHeight", "?"),
            )

            # Create helper instances
            self.locator = create_locator(self.device)
            self.popup_handler = PopupHandler(self.device, self.locator)
            self.actions = UIActions(self.device, self.locator, self.popup_handler)

            # Subclass-specific setup
            self.pre_test_setup()

        except Exception as e:
            logger.error("Setup failed: %s", e)
            self.result.error = f"Setup failed: {e}"
            raise

    def teardown(self):
        """Clean up after test. Called once after the test method."""
        logger.info("-" * 70)
        logger.info("TEARDOWN: [%s] %s", self.TEST_MODULE, self.TEST_NAME)

        try:
            self.post_test_cleanup()
        except Exception as e:
            logger.warning("Post-test cleanup error: %s", e)

        self.result.end_time = datetime.now()
        if self.result.start_time:
            self.result.duration_ms = (
                (self.result.end_time - self.result.start_time).total_seconds() * 1000
            )

        # Log summary
        passed_steps = sum(1 for s in self.result.steps if s.passed)
        total_steps = len(self.result.steps)
        self.result.passed = (
            total_steps > 0
            and passed_steps == total_steps
            and self.result.error is None
        )

        status = "✓ PASSED" if self.result.passed else "✗ FAILED"
        logger.info(
            "%s | Steps: %d/%d passed | Duration: %.0fms",
            status, passed_steps, total_steps, self.result.duration_ms,
        )
        if self.result.error:
            logger.error("Error: %s", self.result.error)

        logger.info("=" * 70)

    def run(self) -> TestCaseResult:
        """
        Full test lifecycle: setup → run_test → teardown.
        Returns TestCaseResult.
        """
        try:
            self.setup()
            self.run_test()
        except Exception as e:
            logger.error("Test execution error: %s", e)
            logger.error(traceback.format_exc())
            self.result.error = str(e)
            self._capture_failure_screenshot("test_error")
        finally:
            self.teardown()

        return self.result

    # ── Abstract Methods ──────────────────────────────────────────────────

    @abstractmethod
    def run_test(self):
        """Subclasses implement this with the actual test logic."""
        ...

    # ── Optional Override Methods ─────────────────────────────────────────

    def pre_test_setup(self):
        """
        Override for test-specific setup before the main test executes.
        Example: grant permissions, launch app, clear app data.
        """
        pass

    def post_test_cleanup(self):
        """
        Override for test-specific cleanup after the main test completes.
        Example: stop app, remove test files, reset state.
        """
        pass

    # ── Step Tracking ─────────────────────────────────────────────────────

    def step(
        self,
        name: str,
        action: Callable[[], Any],
        verify: Optional[Callable[[], bool]] = None,
        timeout: float = DEFAULT_TIMEOUT,
        critical: bool = True,
        screenshot: bool = SCREENSHOT_ON_STEP,
    ) -> TestStepResult:
        """
        Execute a single test step with timing, logging, and result tracking.

        Args:
            name: Human-readable step description.
            action: The callable to execute for this step.
            verify: Optional verification callable (returns bool).
            timeout: Timeout for this step.
            critical: If True, failure aborts the test.
            screenshot: Take screenshot after step execution.

        Returns:
            TestStepResult.
        """
        self._current_step_idx += 1
        step_idx = self._current_step_idx
        logger.info("── Step %d: %s ──", step_idx, name)

        start = time.monotonic()
        step_result = TestStepResult(name=name, passed=False, duration_ms=0.0)

        try:
            # Execute the action
            result = action()

            # Optional verification
            if verify is not None:
                try:
                    verified = verify()
                    if not verified:
                        raise AssertionError(f"Verification failed for step: {name}")
                except Exception as ve:
                    raise AssertionError(f"Verification failed: {ve}") from ve

            step_result.passed = True
            logger.info("  ✓ Step %d passed", step_idx)

        except AssertionError as e:
            step_result.error = str(e)
            logger.error("  ✗ Step %d FAILED (assertion): %s", step_idx, e)
            self._capture_failure_screenshot(f"step_{step_idx}_{name}")

        except Exception as e:
            step_result.error = f"{type(e).__name__}: {e}"
            logger.error("  ✗ Step %d FAILED: %s", step_idx, step_result.error)
            logger.debug(traceback.format_exc())
            self._capture_failure_screenshot(f"step_{step_idx}_{name}")

        finally:
            step_result.duration_ms = (time.monotonic() - start) * 1000
            logger.debug("  Step %d duration: %.0fms", step_idx, step_result.duration_ms)

            if screenshot:
                self._capture_step_screenshot(f"step_{step_idx}_{name}")

        self.result.steps.append(step_result)

        if not step_result.passed and critical:
            self.result.error = step_result.error
            raise AssertionError(
                f"Critical step '{name}' failed: {step_result.error}"
            )

        return step_result

    def optional_step(
        self,
        name: str,
        action: Callable[[], Any],
        timeout: float = SHORT_TIMEOUT,
    ) -> TestStepResult:
        """
        Execute a non-critical step (failure won't abort the test).
        """
        return self.step(name, action, timeout=timeout, critical=False)

    # ── Screenshot Helpers ────────────────────────────────────────────────

    def _capture_failure_screenshot(self, tag: str) -> Optional[Path]:
        """Capture screenshot on failure."""
        if not SCREENSHOT_ON_FAILURE:
            return None
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"FAIL_{self.TEST_MODULE}_{tag}_{timestamp}.{SCREENSHOT_FORMAT}"
            filepath = SCREENSHOT_DIR / filename
            self.device.screenshot(str(filepath))
            self.result.screenshots.append(filepath)
            logger.info("  📸 Failure screenshot: %s", filepath)
            return filepath
        except Exception as e:
            logger.warning("  Could not capture failure screenshot: %s", e)
            return None

    def _capture_step_screenshot(self, tag: str) -> Optional[Path]:
        """Capture step screenshot."""
        if not SCREENSHOT_ON_STEP:
            return None
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"STEP_{self.TEST_MODULE}_{tag}_{timestamp}.{SCREENSHOT_FORMAT}"
            filepath = SCREENSHOT_DIR / filename
            self.device.screenshot(str(filepath))
            self.result.screenshots.append(filepath)
            return filepath
        except Exception:
            return None

    # ── Common Workflow Utilities ─────────────────────────────────────────

    def ensure_app_ready(self) -> bool:
        """
        Ensure the app is launched and the toolbar is visible.
        Handles permission dialogs automatically.
        """
        logger.info("Ensuring app is ready...")

        # Launch app
        launched = self.actions.launch_app()
        if not launched:
            self.result.error = "Failed to launch app"
            return False

        time.sleep(LONG_TIMEOUT * 0.3)

        # Handle overlay permission dialog if present
        self.popup_handler.handle_overlay_permission(accept=True)
        time.sleep(SHORT_TIMEOUT)

        # Check if we need to handle system permission
        self.popup_handler.dismiss_all()
        time.sleep(SHORT_TIMEOUT)

        # Wait for toolbar to appear
        toolbar_visible = self.actions.wait_for_app(timeout=LONG_TIMEOUT)
        if not toolbar_visible:
            # Try launching again
            logger.warning("App not detected, retrying launch...")
            self.actions.launch_app()
            time.sleep(LONG_TIMEOUT * 0.3)
            self.popup_handler.handle_overlay_permission(accept=True)
            self.popup_handler.dismiss_all()
            toolbar_visible = self.actions.wait_for_app(timeout=LONG_TIMEOUT)

        if toolbar_visible:
            logger.info("App is ready (toolbar visible)")
            return True

        # As a last check, try to find any toolbar button
        vis_result = self.locator.find("visibility", timeout=SHORT_TIMEOUT)
        if vis_result.found:
            logger.info("App is ready (visibility button found)")
            return True

        # Dump hierarchy for debugging
        logger.error("App not ready. Dumping hierarchy...")
        self.actions.print_hierarchy_summary()
        return False

    def close_all_popups(self):
        """Aggressively dismiss all popups."""
        for _ in range(3):
            self.popup_handler.dismiss_all()
            time.sleep(0.5)
        self.popup_handler.dismiss_back()

    def click_element_by_coords(self, selector_name: str, timeout: float = DEFAULT_TIMEOUT) -> bool:
        """
        Find an element by selector and click using its bounds center coordinates.

        This avoids the issue where Compose IconButton nodes expose the inner
        Icon's contentDescription but the found node isn't directly clickable.
        By clicking at the center of the element's bounds, we ensure the touch
        hits the parent IconButton.
        """
        result = self.locator.find(selector_name, timeout=timeout)
        if result.found and result.element is not None:
            try:
                info = result.element.info
                bounds = info.get("bounds", {})
                if bounds:
                    cx = (bounds.get("left", 0) + bounds.get("right", 0)) // 2
                    cy = (bounds.get("top", 0) + bounds.get("bottom", 0)) // 2
                    self.device.click(cx, cy)
                    logger.info(
                        "✓ Clicked '%s' at (%d,%d) via bounds center",
                        selector_name, cx, cy
                    )
                    time.sleep(ANIMATION_WAIT)
                    return True
            except Exception as e:
                logger.warning("Bounds click failed for '%s': %s", selector_name, e)
        if result.info.get("coords"):
            x, y = result.info["coords"]
            self.device.click(x, y)
            logger.info("✓ Clicked '%s' at fallback coords (%d,%d)", selector_name, x, y)
            time.sleep(ANIMATION_WAIT)
            return True
        return False

    # ── Reporting Utilities ───────────────────────────────────────────────

    def get_result_summary(self) -> Dict[str, Any]:
        """Get a dictionary summary of test results."""
        return {
            "module": self.result.module,
            "name": self.result.name,
            "passed": self.result.passed,
            "duration_ms": self.result.duration_ms,
            "total_steps": len(self.result.steps),
            "passed_steps": sum(1 for s in self.result.steps if s.passed),
            "failed_steps": sum(1 for s in self.result.steps if not s.passed),
            "error": self.result.error,
            "screenshots": [str(p) for p in self.result.screenshots],
        }
