# -*- coding: utf-8 -*-
"""
DrawAnywhere GUI Automation - Common UI Actions & Popup Handler
=================================================================
Provides high-level UI interaction methods and automatic popup handling.

Features:
- Click, long-click, swipe, drag, input text operations with retry
- Smart drawing stroke simulation
- Automatic system popup detection and dismissal
- Permission dialog handling
- State verification after actions
"""

from __future__ import annotations

import logging
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import uiautomator2 as u2

from config import (
    DEFAULT_TIMEOUT,
    SHORT_TIMEOUT,
    LONG_TIMEOUT,
    POPUP_TIMEOUT,
    IDLE_TIMEOUT,
    ANIMATION_WAIT,
    MAX_RETRIES,
    RETRY_DELAY,
    DRAW_STROKE_STEPS,
    DRAW_STROKE_DURATION,
    SCREENSHOT_DIR,
    SCREENSHOT_ON_FAILURE,
    SCREENSHOT_FORMAT,
    PACKAGE_NAME,
    SELECTORS,
)
from locator import ElementLocator, LocateCriteria, LocatorResult

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Popup Handler
# ────────────────────────────────────────────────────────────────────────────

class PopupHandler:
    """
    Automatic detection and handling of system popups and permission dialogs.

    Handles:
    - Android system permission requests (Allow/Deny)
    - Overlay permission dialogs (custom and system)
    - "App is not responding" dialogs
    - Generic confirmation dialogs

    Usage:
        handler = PopupHandler(device, locator)
        handler.dismiss_all()  # Try to dismiss any visible popup
        # Or use as context manager:
        with handler.auto_dismiss():
            perform_action()
    """

    def __init__(self, device: u2.Device, locator: ElementLocator):
        self.device = device
        self.locator = locator
        self._popup_handled_count = 0

    # ── Popup Detection Patterns ──────────────────────────────────────────

    POPUP_PATTERNS: List[Dict[str, Any]] = [
        # DrawAnywhere overlay permission dialog
        {
            "name": "overlay_permission",
            "title": "permission_dialog_title",
            "accept": "permission_accept",
            "deny": "permission_deny",
            "action": "accept",  # Auto-accept for testing
        },
        # Android system permission dialog
        {
            "name": "system_permission",
            "title": None,
            "accept": "system_allow",
            "deny": "system_deny",
            "action": "accept",
        },
        # Generic "Allow" dialog
        {
            "name": "generic_allow",
            "title": None,
            "accept": "system_confirm",
            "deny": None,
            "action": "accept",
        },
    ]

    def dismiss_all(self, timeout: float = POPUP_TIMEOUT) -> bool:
        """
        Try to detect and dismiss any visible popup.
        Returns True if a popup was handled.
        """
        for pattern in self.POPUP_PATTERNS:
            try:
                if self._handle_popup(pattern, timeout):
                    return True
            except Exception as e:
                logger.debug("Error checking popup '%s': %s", pattern["name"], e)
        return False

    def handle_overlay_permission(self, accept: bool = True) -> bool:
        """
        Specifically handle the DrawAnywhere overlay permission dialog.
        Returns True if the dialog was found and handled.
        """
        # First check for the custom dialog
        title_result = self.locator.find("permission_dialog_title", timeout=POPUP_TIMEOUT)
        if title_result.found:
            logger.info("Overlay permission dialog detected")
            btn_name = "permission_accept" if accept else "permission_deny"
            btn_result = self.locator.find(btn_name, timeout=POPUP_TIMEOUT)
            if btn_result.found and btn_result.element is not None:
                try:
                    btn_result.element.click()
                    logger.info("Clicked '%s' on permission dialog", btn_name)
                    self._popup_handled_count += 1
                    time.sleep(ANIMATION_WAIT)
                    return True
                except Exception as e:
                    logger.error("Failed to click permission button: %s", e)

        # Check for system-level overlay permission
        # (Android Settings → Overlay permission screen)
        try:
            allow_btn = self.device(textMatches=r"(?i)(Allow|允许|Always)")
            if allow_btn.exists:
                allow_btn.click()
                logger.info("Clicked system Allow button for overlay permission")
                self._popup_handled_count += 1
                time.sleep(ANIMATION_WAIT)
                return True
        except Exception:
            pass

        return False

    def _handle_popup(self, pattern: Dict[str, Any], timeout: float) -> bool:
        """Handle a specific popup pattern using fast direct uiautomator2 checks."""
        from config import SELECTORS

        # Fast check using direct uiautomator2 text/description matching (no XML dumps)
        is_present = False
        btn_element = None

        # Check for accept button first (most reliable indicator of a dialog)
        if pattern.get("accept"):
            sel = SELECTORS.get(pattern["accept"], {})
            btn_element = self._fast_find(sel, timeout)
            if btn_element is not None:
                is_present = True

        # Also check for title
        if not is_present and pattern.get("title"):
            sel = SELECTORS.get(pattern["title"], {})
            el = self._fast_find(sel, timeout * 0.5)
            if el is not None:
                is_present = True

        if not is_present:
            return False

        logger.info("Detected popup: %s", pattern["name"])
        action = pattern.get("action", "accept")
        btn_name = pattern.get("accept") if action == "accept" else pattern.get("deny")

        if btn_name and btn_element is None:
            sel = SELECTORS.get(btn_name, {})
            btn_element = self._fast_find(sel, SHORT_TIMEOUT)

        if btn_element is not None:
            try:
                btn_element.click()
                logger.info("Dismissed popup '%s' via '%s'", pattern["name"], btn_name)
                self._popup_handled_count += 1
                time.sleep(ANIMATION_WAIT)
                return True
            except Exception as e:
                logger.error("Failed to click popup button: %s", e)

        return False

    def _fast_find(self, selector: dict, timeout: float):
        """
        Fast element find using direct uiautomator2 calls.
        Avoids expensive XML hierarchy dumps by using built-in selectors.
        """
        import re
        try:
            # Try description regex (fast, no XML dump)
            desc_regex = selector.get("desc_regex")
            if desc_regex and hasattr(desc_regex, 'pattern'):
                # uiautomator2 supports descriptionMatches natively
                el = self.device(descriptionMatches=desc_regex.pattern)
                if el.exists:
                    return el

            # Try text regex
            text_regex = selector.get("text_regex")
            if text_regex and hasattr(text_regex, 'pattern'):
                el = self.device(textMatches=text_regex.pattern)
                if el.exists:
                    return el

            # Try resource ID
            rid = selector.get("resource_id")
            if rid:
                el = self.device(resourceId=rid)
                if el.exists:
                    return el

        except Exception:
            pass

        return None

    def dismiss_back(self, max_attempts: int = 3) -> bool:
        """Try to dismiss a popup by pressing Back."""
        for i in range(max_attempts):
            try:
                self.device.press("back")
                time.sleep(0.5)
                # Check if still has popup
                for pattern in self.POPUP_PATTERNS[:2]:  # Only check permission dialogs
                    if pattern.get("title"):
                        if self.locator.exists(pattern["title"], timeout=0.5):
                            break
                else:
                    logger.info("Popup dismissed via back button")
                    return True
            except Exception:
                pass
        return False

    def auto_dismiss(self):
        """Context manager: automatically dismiss popups during critical operations."""
        return _PopupAutoDismissContext(self)


class _PopupAutoDismissContext:
    """Context manager for automatic popup dismissal."""

    def __init__(self, handler: PopupHandler):
        self.handler = handler

    def __enter__(self):
        # Dismiss any existing popups first
        self.handler.dismiss_all()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Dismiss any popups that appeared during the operation
        self.handler.dismiss_all()
        return False  # Don't suppress exceptions


# ────────────────────────────────────────────────────────────────────────────
# UI Actions
# ────────────────────────────────────────────────────────────────────────────

class UIActions:
    """
    High-level UI interaction methods with automatic retry and logging.

    Provides methods like click, long_click, swipe, drag, draw_stroke,
    and input operations with built-in smart waiting and popup handling.

    Usage:
        actions = UIActions(device, locator, popup_handler)
        actions.click("visibility", timeout=10)
        actions.draw_stroke(from_pos, to_pos)
    """

    def __init__(
        self,
        device: u2.Device,
        locator: ElementLocator,
        popup_handler: PopupHandler,
    ):
        self.device = device
        self.locator = locator
        self.popup = popup_handler
        self.screen_width, self.screen_height = self._get_screen_size()

    # ── Screen Info ───────────────────────────────────────────────────────

    def _get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions."""
        try:
            info = self.device.info
            w = info.get("displayWidth", 1080)
            h = info.get("displayHeight", 1920)
            logger.info("Screen size: %dx%d", w, h)
            return w, h
        except Exception:
            logger.warning("Could not get screen size, using defaults")
            return 1080, 1920

    def refresh_screen_size(self):
        """Refresh cached screen size (after rotation, etc.)."""
        self.screen_width, self.screen_height = self._get_screen_size()

    # ── Click Operations ──────────────────────────────────────────────────

    def click(
        self,
        target: Union[str, LocateCriteria, Tuple[int, int]],
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = MAX_RETRIES,
        wait_after: float = IDLE_TIMEOUT,
    ) -> bool:
        """
        Click an element or coordinates with automatic retry and popup handling.

        Args:
            target: Named selector, LocateCriteria, or (x, y) tuple.
            timeout: Max wait time per attempt.
            retries: Number of retry attempts.
            wait_after: Pause after successful click for UI to settle.

        Returns:
            True if click succeeded.
        """
        for attempt in range(1, retries + 1):
            try:
                # Dismiss popups before attempting
                self.popup.dismiss_all()

                if isinstance(target, tuple):
                    x, y = target
                else:
                    result = self.locator.find(target, timeout=timeout)
                    if not result.found:
                        if result.info.get("coords"):
                            x, y = result.info["coords"]
                        else:
                            logger.warning(
                                "Click attempt %d/%d: element not found", attempt, retries
                            )
                            if attempt < retries:
                                time.sleep(RETRY_DELAY)
                            continue
                    elif result.element is None:
                        logger.warning(
                            "Click attempt %d/%d: element found but None", attempt, retries
                        )
                        if attempt < retries:
                            time.sleep(RETRY_DELAY)
                        continue
                    else:
                        result.element.click()
                        logger.info("✓ Clicked element (attempt %d, strategy: %s)", attempt, result.strategy_used)
                        time.sleep(wait_after)
                        return True

                # Coordinate click
                self.device.click(x, y)
                target_desc = f"({x}, {y})" if isinstance(target, tuple) else str(target)
                logger.info("✓ Clicked at %s (attempt %d)", target_desc, attempt)
                time.sleep(wait_after)
                return True

            except Exception as e:
                logger.warning("Click attempt %d/%d failed: %s", attempt, retries, e)
                if attempt < retries:
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("Click failed after %d attempts: %s", retries, e)
                    if SCREENSHOT_ON_FAILURE:
                        self._screenshot("click_failed")

        return False

    def long_click(
        self,
        target: Union[str, LocateCriteria, Tuple[int, int]],
        duration: float = 1.0,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = MAX_RETRIES,
    ) -> bool:
        """Long-click an element or coordinates."""
        for attempt in range(1, retries + 1):
            try:
                self.popup.dismiss_all()

                if isinstance(target, tuple):
                    x, y = target
                    self.device.long_click(x, y, duration)
                else:
                    result = self.locator.find(target, timeout=timeout)
                    if result.found and result.element is not None:
                        result.element.long_click(duration=duration)
                    elif result.info.get("coords"):
                        x, y = result.info["coords"]
                        self.device.long_click(x, y, duration)
                    else:
                        if attempt < retries:
                            time.sleep(RETRY_DELAY)
                            continue
                        return False

                logger.info("✓ Long-clicked (attempt %d)", attempt)
                time.sleep(IDLE_TIMEOUT)
                return True

            except Exception as e:
                logger.warning("Long-click attempt %d/%d failed: %s", attempt, retries, e)
                if attempt < retries:
                    time.sleep(RETRY_DELAY)

        return False

    def double_click(
        self,
        target: Union[str, LocateCriteria, Tuple[int, int]],
        timeout: float = DEFAULT_TIMEOUT,
    ) -> bool:
        """Double-click an element."""
        if self.click(target, timeout=timeout, wait_after=0.1):
            return self.click(target, timeout=SHORT_TIMEOUT, wait_after=IDLE_TIMEOUT)
        return False

    # ── Swipe / Scroll ────────────────────────────────────────────────────

    def swipe(
        self,
        direction: str = "up",
        distance: float = 0.5,
        duration: float = 0.3,
    ) -> bool:
        """
        Swipe on the screen.

        Args:
            direction: "up", "down", "left", "right"
            distance: Fraction of screen dimension to swipe (0.0-1.0)
            duration: Swipe duration in seconds.
        """
        w, h = self.screen_width, self.screen_height
        cx, cy = w // 2, h // 2

        if direction == "up":
            fx, fy = cx, int(cy + cy * distance)
            tx, ty = cx, int(cy - cy * distance)
        elif direction == "down":
            fx, fy = cx, int(cy - cy * distance)
            tx, ty = cx, int(cy + cy * distance)
        elif direction == "left":
            fx, fy = int(cx + cx * distance), cy
            tx, ty = int(cx - cx * distance), cy
        elif direction == "right":
            fx, fy = int(cx - cx * distance), cy
            tx, ty = int(cx + cx * distance), cy
        else:
            logger.error("Unknown swipe direction: %s", direction)
            return False

        try:
            self.device.swipe(fx, fy, tx, ty, duration)
            logger.info("✓ Swiped %s (%.2f screen)", direction, distance)
            time.sleep(ANIMATION_WAIT)
            return True
        except Exception as e:
            logger.error("Swipe failed: %s", e)
            return False

    def swipe_element(
        self,
        target: Union[str, LocateCriteria],
        direction: str = "up",
        distance: float = 0.3,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> bool:
        """Swipe on a specific element."""
        result = self.locator.find(target, timeout=timeout)
        if result.found and result.element is not None:
            try:
                result.element.swipe(direction, steps=int(distance * 100))
                logger.info("✓ Swiped element %s", direction)
                time.sleep(ANIMATION_WAIT)
                return True
            except Exception as e:
                logger.error("Element swipe failed: %s", e)
        return False

    # ── Drawing Simulation ────────────────────────────────────────────────

    def draw_stroke(
        self,
        from_pos: Tuple[int, int],
        to_pos: Tuple[int, int],
        steps: int = DRAW_STROKE_STEPS,
        duration: float = DRAW_STROKE_DURATION,
    ) -> bool:
        """
        Simulate a drawing stroke from one point to another.

        Uses multiple intermediate points to create a smooth-looking stroke.

        Args:
            from_pos: Starting (x, y) coordinates.
            to_pos: Ending (x, y) coordinates.
            steps: Number of intermediate touch points.
            duration: Total stroke duration in seconds.
        """
        x1, y1 = from_pos
        x2, y2 = to_pos

        try:
            # Use swipe for smooth line drawing
            self.device.swipe(x1, y1, x2, y2, duration, steps=steps)
            logger.info(
                "✓ Drew stroke: (%d,%d) → (%d,%d) [%d steps, %.2fs]",
                x1, y1, x2, y2, steps, duration
            )
            time.sleep(ANIMATION_WAIT)
            return True
        except Exception as e:
            logger.error("Draw stroke failed: %s", e)
            return False

    def draw_shape(
        self,
        shape: str = "line",
        center: Optional[Tuple[int, int]] = None,
        size: float = 0.3,
        duration: float = 1.0,
    ) -> bool:
        """
        Draw a shape on the canvas.

        Args:
            shape: "line", "circle", "square", "triangle", "zigzag"
            center: Center point (defaults to screen center).
            size: Relative size (fraction of screen width).
            duration: Drawing duration.
        """
        w, h = self.screen_width, self.screen_height
        if center is None:
            center = (w // 2, h // 2)

        cx, cy = center
        sz = int(w * size)

        try:
            if shape == "line":
                self.device.swipe(cx - sz, cy, cx + sz, cy, duration)
            elif shape == "circle":
                # Approximate circle with multiple swipes
                import math
                radius = sz // 2
                segments = 36
                points = []
                for i in range(segments + 1):
                    angle = 2 * math.pi * i / segments
                    px = cx + int(radius * math.cos(angle))
                    py = cy + int(radius * math.sin(angle))
                    points.append((px, py))

                # Execute multi-point swipe via touch events
                self.device.touch.down(*points[0])
                for px, py in points[1:]:
                    self.device.touch.move(px, py)
                    time.sleep(duration / len(points))
                self.device.touch.up(*points[-1])

            elif shape == "square":
                half = sz // 2
                self.device.swipe(cx - half, cy - half, cx + half, cy - half, duration / 4)
                self.device.swipe(cx + half, cy - half, cx + half, cy + half, duration / 4)
                self.device.swipe(cx + half, cy + half, cx - half, cy + half, duration / 4)
                self.device.swipe(cx - half, cy + half, cx - half, cy - half, duration / 4)

            elif shape == "triangle":
                half = sz // 2
                top = (cx, cy - half)
                bottom_left = (cx - half, cy + half)
                bottom_right = (cx + half, cy + half)
                self.device.swipe(*top, *bottom_right, duration / 3)
                self.device.swipe(*bottom_right, *bottom_left, duration / 3)
                self.device.swipe(*bottom_left, *top, duration / 3)

            elif shape == "zigzag":
                segments = 5
                seg_w = sz * 2 // segments
                amp = sz // 3
                x = cx - sz
                for i in range(segments):
                    y_dir = 1 if i % 2 == 0 else -1
                    nx = x + seg_w
                    ny = cy + y_dir * amp
                    self.device.swipe(x, cy, nx, ny, duration / segments)
                    x, cy = nx, ny

            logger.info("✓ Drew %s shape at (%d,%d)", shape, cx, cy)
            time.sleep(ANIMATION_WAIT)
            return True

        except Exception as e:
            logger.error("Draw shape '%s' failed: %s", shape, e)
            return False

    # ── Text Input ────────────────────────────────────────────────────────

    def input_text(
        self,
        text: str,
        target: Optional[Union[str, LocateCriteria]] = None,
        clear_first: bool = True,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Input text into a field.

        Args:
            text: The text to input.
            target: The input field selector. If None, types to focused field.
            clear_first: Clear existing text before typing.
        """
        try:
            if target is not None:
                if not self.click(target, timeout=timeout):
                    return False

            if clear_first:
                self.device.clear_text()

            self.device.send_keys(text)
            logger.info("✓ Input text: '%s'", text)
            time.sleep(IDLE_TIMEOUT)
            return True
        except Exception as e:
            logger.error("Input text failed: %s", e)
            return False

    # ── Navigation ────────────────────────────────────────────────────────

    def press_back(self, times: int = 1) -> bool:
        """Press Android back button."""
        for i in range(times):
            try:
                self.device.press("back")
                time.sleep(ANIMATION_WAIT)
            except Exception as e:
                logger.error("Back press failed: %s", e)
                return False
        logger.info("✓ Pressed back %d time(s)", times)
        return True

    def press_home(self) -> bool:
        """Press Android home button."""
        try:
            self.device.press("home")
            time.sleep(IDLE_TIMEOUT)
            logger.info("✓ Pressed home")
            return True
        except Exception as e:
            logger.error("Home press failed: %s", e)
            return False

    def press_recent(self) -> bool:
        """Press Android recent apps button."""
        try:
            self.device.press("recent")
            time.sleep(IDLE_TIMEOUT)
            logger.info("✓ Pressed recent apps")
            return True
        except Exception as e:
            logger.error("Recent press failed: %s", e)
            return False

    # ── App Management ────────────────────────────────────────────────────

    def launch_app(self, wait: bool = True) -> bool:
        """
        Launch the DrawAnywhere app.

        Returns True if the app was launched (or already running).
        """
        try:
            self.device.app_start(PACKAGE_NAME, wait=wait)
            time.sleep(LONG_TIMEOUT * 0.5)  # Wait for app to initialize
            logger.info("✓ App launched: %s", PACKAGE_NAME)
            return True
        except Exception as e:
            logger.error("Failed to launch app: %s", e)
            return False

    def stop_app(self) -> bool:
        """Force stop the DrawAnywhere app."""
        try:
            self.device.app_stop(PACKAGE_NAME)
            time.sleep(IDLE_TIMEOUT)
            logger.info("✓ App stopped: %s", PACKAGE_NAME)
            return True
        except Exception as e:
            logger.error("Failed to stop app: %s", e)
            return False

    def is_app_running(self) -> bool:
        """Check if DrawAnywhere is running."""
        try:
            info = self.device.app_info(PACKAGE_NAME)
            return info is not None
        except Exception:
            return False

    def wait_for_app(self, timeout: float = LONG_TIMEOUT) -> bool:
        """Wait for the app to be visible."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                current = self.device.app_current()
                if current and current.get("package") == PACKAGE_NAME:
                    logger.info("✓ App is in foreground")
                    return True
            except Exception:
                pass
            time.sleep(0.5)

        # App might be running as a service (overlay mode)
        # Check if the toolbar is visible instead
        vis_result = self.locator.exists("visibility", timeout=SHORT_TIMEOUT)
        if vis_result:
            logger.info("✓ App overlay detected (toolbar visible)")
            return True

        logger.warning("App not detected in foreground after %.0fs", timeout)
        return False

    # ── Verification Helpers ──────────────────────────────────────────────

    def verify_element_exists(
        self, target: Union[str, LocateCriteria], timeout: float = SHORT_TIMEOUT
    ) -> bool:
        """Verify an element is present on screen."""
        result = self.locator.find(target, timeout=timeout)
        return result.found

    def verify_element_not_exists(
        self, target: Union[str, LocateCriteria], timeout: float = SHORT_TIMEOUT
    ) -> bool:
        """Verify an element is NOT present."""
        result = self.locator.find(target, timeout=timeout)
        return not result.found

    def verify_element_enabled(
        self, target: Union[str, LocateCriteria], timeout: float = SHORT_TIMEOUT
    ) -> bool:
        """Verify an element is enabled."""
        result = self.locator.find(target, timeout=timeout)
        if result.found and result.element is not None:
            try:
                info = result.element.info
                return info.get("enabled", False)
            except Exception:
                pass
        return False

    def verify_text_visible(self, text: str, timeout: float = DEFAULT_TIMEOUT) -> bool:
        """Verify specific text is visible on screen."""
        try:
            el = self.device(text=text)
            return el.wait(timeout=timeout)
        except Exception:
            return False

    # ── Screenshot ────────────────────────────────────────────────────────

    def _screenshot(self, name: str = "action") -> Optional[Path]:
        """Take a debug screenshot."""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.{SCREENSHOT_FORMAT}"
            filepath = SCREENSHOT_DIR / filename
            self.device.screenshot(str(filepath))
            logger.debug("Screenshot: %s", filepath)
            return filepath
        except Exception as e:
            logger.error("Screenshot failed: %s", e)
            return None

    def screenshot(self, name: str = "manual") -> Optional[Path]:
        """Public method to take a screenshot."""
        return self._screenshot(name)

    # ── Dump Hierarchy ────────────────────────────────────────────────────

    def dump_hierarchy(self) -> Optional[str]:
        """Dump current UI hierarchy for debugging."""
        try:
            xml = self.device.dump_hierarchy()
            logger.debug("UI hierarchy: %d chars", len(xml))
            return xml
        except Exception as e:
            logger.error("Failed to dump hierarchy: %s", e)
            return None

    def print_hierarchy_summary(self):
        """Print a summary of important UI elements."""
        try:
            xml = self.device.dump_hierarchy()
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml)

            clickable_nodes = []
            for node in root.iter("node"):
                if node.get("clickable") == "true":
                    desc = node.get("content-desc", "")
                    text = node.get("text", "")
                    cls = node.get("class", "")
                    if desc or text:
                        clickable_nodes.append(f"  [{cls}] desc='{desc}' text='{text}'")

            if clickable_nodes:
                logger.info("Clickable elements on screen:\n%s", "\n".join(clickable_nodes[:30]))
            else:
                logger.info("No clickable elements with descriptions found")

        except Exception as e:
            logger.error("Failed to print hierarchy summary: %s", e)
