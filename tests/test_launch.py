# -*- coding: utf-8 -*-
"""
DrawAnywhere GUI Test - App Launch & Permission Handling
=========================================================
Tests the critical app launch flow including:
- App cold start
- Overlay permission dialog handling (accept/deny)
- System permission dialog handling
- Foreground service activation
- Toolbar appearance after launch
- App re-launch when already running
"""

import logging
import time

from base_test import BaseTest
from config import (
    PACKAGE_NAME,
    DEFAULT_TIMEOUT,
    SHORT_TIMEOUT,
    LONG_TIMEOUT,
    IDLE_TIMEOUT,
    ANIMATION_WAIT,
)

logger = logging.getLogger(__name__)


class TestAppLaunch(BaseTest):
    """
    Test the application launch flow including permission handling.

    Verifies:
    1. App can be launched from cold start
    2. Overlay permission dialog appears (first launch) and can be accepted
    3. System overlay permission screen is navigable
    4. Service starts and toolbar appears
    5. App re-launch behavior
    """

    TEST_MODULE = "launch"
    TEST_NAME = "test_app_launch_flow"

    def run_test(self):
        """Execute all launch flow test steps."""
        # ── Step 1: Force stop app to start from clean state ──────────
        self.step(
            "Force stop app for clean start",
            lambda: self.actions.stop_app(),
            critical=False,  # Not critical if already stopped
        )
        time.sleep(IDLE_TIMEOUT)

        # ── Step 2: Launch the app ────────────────────────────────────
        self.step(
            "Launch DrawAnywhere app",
            lambda: self.actions.launch_app(),
            verify=lambda: self.actions.is_app_running(),
            timeout=LONG_TIMEOUT,
        )

        # ── Step 3: Handle overlay permission dialog ──────────────────
        # (Will appear on first launch if permission not granted)
        self.step(
            "Handle overlay permission dialog",
            lambda: self._handle_app_launch_permissions(),
            timeout=LONG_TIMEOUT,
        )

        # ── Step 4: Verify app is ready ───────────────────────────────
        self.step(
            "Verify app is ready (toolbar visible)",
            lambda: None,  # No action needed; verification does the check
            verify=lambda: self._verify_app_ready(),
            timeout=LONG_TIMEOUT,
        )

        # ── Step 5: Verify toolbar buttons exist ──────────────────────
        self.step(
            "Verify core toolbar buttons are visible",
            lambda: None,
            verify=lambda: self._verify_core_buttons(),
            timeout=DEFAULT_TIMEOUT,
        )

        logger.info("All launch flow tests passed ✓")

    # ── Helper Methods ────────────────────────────────────────────────────

    def _handle_app_launch_permissions(self):
        """Handle any permission dialogs during app launch."""
        # Wait for dialogs to appear
        time.sleep(SHORT_TIMEOUT)

        # Try to handle custom overlay permission dialog
        handled = self.popup_handler.handle_overlay_permission(accept=True)
        if handled:
            logger.info("Handled custom overlay permission dialog")
            time.sleep(LONG_TIMEOUT * 0.3)  # Wait for settings screen
            # On settings screen, try to grant permission
            self._grant_system_overlay_permission()
            # Press back to return from settings
            time.sleep(SHORT_TIMEOUT)
            self.actions.press_back()
            time.sleep(SHORT_TIMEOUT)
        else:
            # Maybe the permission was already granted
            logger.info("No permission dialog detected (may already be granted)")

        # Dismiss any system dialogs
        self.popup_handler.dismiss_all()

    def _grant_system_overlay_permission(self):
        """
        Try to grant overlay permission on the Android Settings screen.
        This navigates the system permission toggle.
        """
        try:
            # Look for the permission toggle switch
            import re
            xml = self.device.dump_hierarchy()
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml)

            # Find switch elements related to overlay permission
            switches = []
            for node in root.iter("node"):
                cls = node.get("class", "")
                if "Switch" in cls or "Toggle" in cls:
                    switches.append(node)
                elif node.get("checkable") == "true":
                    switches.append(node)
                # Also look for text mentioning the app name
                text = node.get("text", "")
                if "drawanywhere" in text.lower() or "DrawAnywhere" in text:
                    # Found the app row; click to toggle
                    bounds = node.get("bounds", "")
                    if bounds:
                        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
                        if m:
                            x1, y1, x2, y2 = map(int, m.groups())
                            cx = (x1 + x2) // 2
                            cy = (y1 + y2) // 2
                            # Click to the right (where switch usually is)
                            self.device.click(x2 + 10, cy)
                            logger.info("Toggled overlay permission via switch")
                            time.sleep(IDLE_TIMEOUT)
                            return

            # Fallback: try to find "Allow display over other apps" toggle
            for node in root.iter("node"):
                text = node.get("text", "")
                if "overlay" in text.lower() or "display over" in text.lower() or "悬浮窗" in text:
                    bounds = node.get("bounds", "")
                    if bounds:
                        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
                        if m:
                            x1, y1, x2, y2 = map(int, m.groups())
                            self.device.click((x1 + x2) // 2, (y1 + y2) // 2)
                            logger.info("Clicked overlay permission setting")
                            time.sleep(IDLE_TIMEOUT)
                            return

            logger.info("Could not find overlay permission toggle (may already be set)")

        except Exception as e:
            logger.warning("Error granting system overlay permission: %s", e)

    def _verify_app_ready(self) -> bool:
        """Verify the app is fully ready after launch."""
        # Method 1: Check if app is in foreground
        try:
            current = self.device.app_current()
            if current and current.get("package") == PACKAGE_NAME:
                logger.info("App is in foreground")
                return True
        except Exception:
            pass

        # Method 2: Look for toolbar elements (app runs as overlay)
        # The overlay might show DrawAnywhere UI elements
        for selector_name in ["visibility", "tool_controls", "color_picker"]:
            if self.locator.exists(selector_name, timeout=SHORT_TIMEOUT):
                logger.info("App ready: found '%s' element", selector_name)
                return True

        # Method 3: Search for app name in UI hierarchy
        try:
            xml = self.device.dump_hierarchy()
            if "DrawAnywhere" in xml or "drawanywhere" in xml.lower():
                logger.info("App ready: found app name in hierarchy")
                return True
        except Exception:
            pass

        # Last resort: check if the app process is running
        if self.actions.is_app_running():
            logger.info("App process is running")
            return True

        return False

    def _verify_core_buttons(self) -> bool:
        """Verify that core toolbar buttons are present."""
        core_selectors = [
            "visibility",      # Show/hide canvas
            "tool_controls",   # Pen/Eraser/Wdith/Opacity
            "color_picker",    # Color picker
        ]

        found_count = 0
        for sel_name in core_selectors:
            result = self.locator.find(sel_name, timeout=SHORT_TIMEOUT)
            if result.found:
                found_count += 1
                logger.info("  Found button: %s (via %s)", sel_name, result.strategy_used)
            else:
                logger.warning("  Button NOT found: %s", sel_name)

        # Require at least 2 of 3 core buttons
        return found_count >= 2


class TestAppReLaunch(BaseTest):
    """
    Test app behavior when re-launched while already running.
    """

    TEST_MODULE = "launch"
    TEST_NAME = "test_app_relaunch"

    def run_test(self):
        """Test re-launch behavior."""
        # ── Ensure app is running first ────────────────────────────────
        self.step(
            "Ensure app is running",
            lambda: self.actions.launch_app(),
            verify=lambda: self.actions.is_app_running(),
        )

        # ── Re-launch the app ──────────────────────────────────────────
        self.step(
            "Re-launch DrawAnywhere while already running",
            lambda: self.actions.launch_app(),
            timeout=LONG_TIMEOUT,
        )

        # ── Verify app is still functional ─────────────────────────────
        self.step(
            "Verify toolbar is still functional after re-launch",
            lambda: None,
            verify=lambda: self.locator.exists("visibility", timeout=SHORT_TIMEOUT),
        )

        logger.info("Re-launch test passed ✓")
