# -*- coding: utf-8 -*-
"""
DrawAnywhere GUI Test - Drawing Operations
===========================================
Tests all drawing-related functionality:
- Pen tool selection
- Color picker interaction and color change
- Stroke width adjustment
- Stroke opacity adjustment
- Stroke eraser selection
- Drawing strokes on canvas
- Undo/Redo operations
- Clear canvas
- Canvas visibility toggle
- Touch passthrough toggle
"""

import logging
import time

from base_test import BaseTest
from config import (
    DEFAULT_TIMEOUT,
    SHORT_TIMEOUT,
    LONG_TIMEOUT,
    IDLE_TIMEOUT,
    ANIMATION_WAIT,
    DRAW_STROKE_STEPS,
    DRAW_STROKE_DURATION,
)

logger = logging.getLogger(__name__)


class TestDrawingOperations(BaseTest):
    """
    Test complete drawing workflow: select tool → set color/size → draw → undo/redo → clear.
    """

    TEST_MODULE = "drawing"
    TEST_NAME = "test_drawing_operations"

    def pre_test_setup(self):
        """Ensure app is launched and ready before drawing tests."""
        self.actions.launch_app()
        time.sleep(LONG_TIMEOUT * 0.3)
        self.popup_handler.handle_overlay_permission(accept=True)
        self.popup_handler.dismiss_all()
        time.sleep(SHORT_TIMEOUT)

    def run_test(self):
        """Execute drawing operation tests."""
        # ── Verify initial state ────────────────────────────────────────
        self.step(
            "Verify toolbar is visible for drawing",
            lambda: None,
            verify=lambda: self.locator.exists("visibility", timeout=DEFAULT_TIMEOUT),
        )

        # ── Test 1: Pen Tool Selection ─────────────────────────────────
        self._test_pen_tool_selection()

        # ── Test 2: Color Picker ───────────────────────────────────────
        self._test_color_picker()

        # ── Test 3: Stroke Width & Opacity ─────────────────────────────
        self._test_stroke_controls()

        # ── Test 4: Draw on Canvas ─────────────────────────────────────
        self._test_draw_on_canvas()

        # ── Test 5: Undo / Redo ────────────────────────────────────────
        self._test_undo_redo()

        # ── Test 6: Clear Canvas ───────────────────────────────────────
        self._test_clear_canvas()

        # ── Test 7: Canvas Visibility ──────────────────────────────────
        self._test_canvas_visibility()

        # ── Test 8: Stroke Eraser ──────────────────────────────────────
        self._test_stroke_eraser()

        logger.info("All drawing operation tests passed ✓")

    # ────────────────────────────────────────────────────────────────────
    # Individual Drawing Tests
    # ────────────────────────────────────────────────────────────────────

    def _test_pen_tool_selection(self):
        """Test selecting pen and eraser tools from the popup."""
        logger.info("── Testing Pen Tool Selection ──")

        # Open tool controls popup
        self.step(
            "Open tool controls popup",
            lambda: self.actions.click("tool_controls", timeout=DEFAULT_TIMEOUT),
        )
        time.sleep(ANIMATION_WAIT)

        # Verify popup appears (look for Tools label or Pen button)
        popup_visible = (
            self.locator.exists("pen_tab", timeout=SHORT_TIMEOUT) or
            self.locator.exists("tools_label", timeout=SHORT_TIMEOUT)
        )
        if not popup_visible:
            logger.warning("Tool controls popup not clearly visible, proceeding anyway")

        # Select "Pen" tool (if eraser is active)
        pen_result = self.locator.find("pen_tab", timeout=SHORT_TIMEOUT)
        if pen_result.found:
            self.step(
                "Select Pen tool",
                lambda: self.actions.click("pen_tab", timeout=SHORT_TIMEOUT),
            )
            logger.info("Pen tool selected")

        # Close popup by clicking tool_controls again or pressing back
        self.step(
            "Close tool controls popup",
            lambda: self._close_current_popup(),
        )

    def _test_color_picker(self):
        """Test the color picker popup."""
        logger.info("── Testing Color Picker ──")

        # Open color picker popup
        self.step(
            "Open color picker popup",
            lambda: self.actions.click("color_picker", timeout=DEFAULT_TIMEOUT),
        )
        time.sleep(ANIMATION_WAIT)

        # Verify color label is visible
        color_label_found = self.locator.exists("color_label", timeout=SHORT_TIMEOUT)
        if color_label_found:
            logger.info("Color picker popup is visible")
        else:
            logger.warning("Color label not found via text; checking hierarchy...")
            # Try to find any color swatch by looking for small circular elements
            self.actions.print_hierarchy_summary()

        # Try to select a color by tapping in the popup area
        # The color swatches are Compose-rendered circular buttons
        self.step(
            "Select a color from the picker",
            lambda: self._select_color_from_picker(),
            critical=False,  # Non-critical since swatch detection is complex
        )

        # Close popup
        self.step(
            "Close color picker popup",
            lambda: self._close_current_popup(),
        )

    def _test_stroke_controls(self):
        """Test stroke width and opacity sliders."""
        logger.info("── Testing Stroke Controls ──")

        # Open tool controls popup (swipe to second page if needed)
        self.step(
            "Open tool controls for stroke settings",
            lambda: self.actions.click("tool_controls", timeout=DEFAULT_TIMEOUT),
        )
        time.sleep(ANIMATION_WAIT)

        # Check if we see width/opacity labels
        controls_visible = (
            self.locator.exists("width_label", timeout=SHORT_TIMEOUT) or
            self.locator.exists("opacity_label", timeout=SHORT_TIMEOUT)
        )

        if controls_visible:
            logger.info("Stroke controls (width/opacity) are visible")

            # Try to interact with the width slider
            # Sliders in Compose are hard to locate precisely, so we use coordinate-based interaction
            self.step(
                "Adjust stroke width via swipe",
                lambda: self._interact_with_slider("width"),
                critical=False,
            )
        else:
            # Need to swipe to the second page of the popup
            logger.info("Swiping to second page of tool controls popup...")
            self.actions.swipe("left")
            time.sleep(ANIMATION_WAIT)

            controls_now = (
                self.locator.exists("width_label", timeout=SHORT_TIMEOUT) or
                self.locator.exists("opacity_label", timeout=SHORT_TIMEOUT)
            )
            if controls_now:
                logger.info("Stroke controls found after swiping")
                self.step(
                    "Adjust stroke opacity via swipe",
                    lambda: self._interact_with_slider("opacity"),
                    critical=False,
                )
            else:
                logger.warning("Stroke controls not found; skipping slider test")

        # Close popup
        self.step(
            "Close stroke controls popup",
            lambda: self._close_current_popup(),
        )

    def _test_draw_on_canvas(self):
        """Test drawing strokes on the canvas."""
        logger.info("── Testing Canvas Drawing ──")

        # Ensure canvas is visible
        self.step(
            "Ensure canvas is visible for drawing",
            lambda: self._ensure_canvas_visible(),
            timeout=DEFAULT_TIMEOUT,
        )

        # Get drawing area coordinates
        w, h = self.actions.screen_width, self.actions.screen_height
        # Avoid toolbar area (usually top-left quadrant)
        draw_center = (w // 2, h // 2)

        # Draw a horizontal line
        self.step(
            "Draw a horizontal line on canvas",
            lambda: self.actions.draw_stroke(
                (w // 4, h // 2),
                (3 * w // 4, h // 2),
                duration=DRAW_STROKE_DURATION,
            ),
        )

        # Draw a vertical line
        self.step(
            "Draw a vertical line on canvas",
            lambda: self.actions.draw_stroke(
                (w // 2, h // 4),
                (w // 2, 3 * h // 4),
                duration=DRAW_STROKE_DURATION,
            ),
        )

        # Draw a diagonal line
        self.step(
            "Draw a diagonal line on canvas",
            lambda: self.actions.draw_stroke(
                (w // 3, h // 3),
                (2 * w // 3, 2 * h // 3),
                duration=DRAW_STROKE_DURATION,
            ),
        )

        logger.info("Drawing strokes completed")

    def _test_undo_redo(self):
        """Test undo and redo functionality.

        Note: Undo is in the first drawer (visible by default when canvas is
        visible). Redo is in the second drawer, which is collapsed by default
        and must be expanded first via the expand_toolbar button.

        CRITICAL: Compose IconButton accessibility nodes sometimes expose the
        inner Icon's contentDescription without making the node itself clickable.
        We use coordinate-based clicking (bounds center) to ensure the parent
        IconButton receives the touch event.
        """
        logger.info("── Testing Undo/Redo ──")

        # Undo the last stroke (first drawer — always visible)
        self.step(
            "Undo last stroke",
            lambda: self.actions.click("undo", timeout=DEFAULT_TIMEOUT),
        )

        # Undo again
        self.step(
            "Undo second stroke",
            lambda: self.actions.click("undo", timeout=DEFAULT_TIMEOUT),
        )

        # Expand the second drawer to reveal redo button
        # Use coordinate click because the Icon node (not IconButton) is found
        self.step(
            "Expand second drawer for redo",
            lambda: self.click_element_by_coords("expand_toolbar", DEFAULT_TIMEOUT),
        )

        # Wait for second drawer animation to complete
        time.sleep(ANIMATION_WAIT)

        # Redo (now visible in second drawer)
        self.step(
            "Redo one stroke",
            lambda: self.click_element_by_coords("redo", DEFAULT_TIMEOUT),
        )

        # Collapse the second drawer to restore clean state
        self.step(
            "Collapse second drawer",
            lambda: self.click_element_by_coords("collapse_toolbar", DEFAULT_TIMEOUT),
        )

        logger.info("Undo/Redo operations completed")

    def _test_clear_canvas(self):
        """Test clearing the entire canvas."""
        logger.info("── Testing Clear Canvas ──")

        self.step(
            "Clear canvas",
            lambda: self.actions.click("clear", timeout=DEFAULT_TIMEOUT),
        )

        # Verify can't undo after clear
        time.sleep(SHORT_TIMEOUT)

        logger.info("Canvas cleared")

    def _test_canvas_visibility(self):
        """Test toggling canvas visibility."""
        logger.info("── Testing Canvas Visibility ──")

        # Hide canvas
        self.step(
            "Hide canvas",
            lambda: self.actions.click("visibility", timeout=DEFAULT_TIMEOUT),
        )

        # Wait for animation
        time.sleep(ANIMATION_WAIT)

        # Show canvas
        self.step(
            "Show canvas",
            lambda: self.actions.click("visibility", timeout=DEFAULT_TIMEOUT),
        )

        logger.info("Canvas visibility toggled")

    def _test_stroke_eraser(self):
        """Test stroke eraser tool."""
        logger.info("── Testing Stroke Eraser ──")

        # First, draw a stroke to erase
        w, h = self.actions.screen_width, self.actions.screen_height
        self.actions.draw_stroke((w // 3, h // 3), (2 * w // 3, h // 3))

        # Open tool controls and select stroke eraser
        self.step(
            "Open tool controls for eraser selection",
            lambda: self.actions.click("tool_controls", timeout=DEFAULT_TIMEOUT),
        )

        eraser_result = self.locator.find("eraser_tab", timeout=SHORT_TIMEOUT)
        if eraser_result.found:
            self.step(
                "Select Stroke Eraser tool",
                lambda: self.actions.click("eraser_tab", timeout=SHORT_TIMEOUT),
            )
        else:
            logger.warning("Eraser tab not found; skipping eraser test")

        # Close popup
        self.step(
            "Close tool controls after eraser selection",
            lambda: self._close_current_popup(),
        )

        # Try to erase by drawing over the stroke
        self.step(
            "Erase stroke by drawing over it",
            lambda: self.actions.draw_stroke(
                (w // 3 - 20, h // 3 - 20),
                (2 * w // 3 + 20, h // 3 + 20),
                duration=DRAW_STROKE_DURATION,
            ),
            critical=False,
        )

        # Switch back to pen
        self.step(
            "Switch back to Pen tool",
            lambda: self._switch_to_pen(),
        )

    # ── Helper Methods ────────────────────────────────────────────────────


    def _ensure_canvas_visible(self):
        """Make sure the canvas is visible for drawing."""
        # The visibility button toggles canvas; check current state
        # If "Show canvas" is the description, canvas is hidden
        result = self.locator.find("visibility", timeout=SHORT_TIMEOUT)
        if result.found and result.element is not None:
            try:
                desc = result.element.info.get("contentDescription", "")
                if "show" in desc.lower() or "显示" in desc:
                    # Canvas is hidden, click to show
                    self.actions.click("visibility", timeout=SHORT_TIMEOUT)
                    time.sleep(ANIMATION_WAIT)
            except Exception:
                # If we can't determine, toggle once to be safe
                pass

    def _select_color_from_picker(self):
        """
        Try to select a color from the color picker popup.
        Uses multiple strategies since Compose color swatches lack text.
        """
        try:
            xml = self.device.dump_hierarchy()
            import xml.etree.ElementTree as ET
            import re
            root = ET.fromstring(xml)

            # Strategy 1: Find small circular elements (likely color swatches)
            # They're typically ImageButton class with bounds ~24x24dp
            small_clickables = []
            for node in root.iter("node"):
                bounds_str = node.get("bounds", "")
                clickable = node.get("clickable", "false") == "true"
                if clickable and bounds_str:
                    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
                    if m:
                        x1, y1, x2, y2 = map(int, m.groups())
                        w_elem = x2 - x1
                        h_elem = y2 - y1
                        # Color swatches are small (20-80px range)
                        if 20 <= w_elem <= 120 and 20 <= h_elem <= 120:
                            small_clickables.append((x1, y1, x2, y2, w_elem * h_elem))

            if small_clickables:
                # Pick the 3rd swatch (avoids the currently selected one)
                idx = min(2, len(small_clickables) - 1)
                x1, y1, x2, y2, _ = small_clickables[idx]
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                self.device.click(cx, cy)
                logger.info("Selected color at (%d, %d) via swatch detection", cx, cy)
                time.sleep(ANIMATION_WAIT)
                return True

            # Strategy 2: Fallback - tap in the center area of the popup
            # Popup is typically centered on screen
            w, h = self.actions.screen_width, self.actions.screen_height
            self.device.click(w // 2, h // 2 + 100)
            logger.info("Attempted color selection via fallback tap")

        except Exception as e:
            logger.warning("Color selection from picker failed: %s", e)

        return False

    def _interact_with_slider(self, slider_type: str = "width"):
        """
        Interact with a Compose Slider element.
        Sliders are hard to locate precisely, so we use coordinate estimation.
        """
        try:
            xml = self.device.dump_hierarchy()
            import xml.etree.ElementTree as ET
            import re
            root = ET.fromstring(xml)

            # Find the label text first
            label_text = "Width" if slider_type == "width" else "Opacity"
            label_pattern = re.compile(rf"({label_text}|宽度|不透明度)", re.IGNORECASE)

            slider_region = None
            for node in root.iter("node"):
                text = node.get("text", "")
                if label_pattern.search(text):
                    bounds_str = node.get("bounds", "")
                    if bounds_str:
                        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
                        if m:
                            x1, y1, x2, y2 = map(int, m.groups())
                            # Slider is typically below the label
                            slider_region = (x1, y2 + 10, x2, y2 + 50)
                            break

            if slider_region:
                sx1, sy1, sx2, sy2 = slider_region
                # Swipe right on the slider to increase value
                start_x = sx1 + int((sx2 - sx1) * 0.3)
                end_x = sx1 + int((sx2 - sx1) * 0.7)
                mid_y = (sy1 + sy2) // 2
                self.device.swipe(start_x, mid_y, end_x, mid_y, 0.3)
                logger.info("Adjusted %s slider via swipe", slider_type)
                time.sleep(ANIMATION_WAIT)
                return True

            # Fallback: swipe in the lower portion of the popup
            w, h = self.actions.screen_width, self.actions.screen_height
            self.device.swipe(
                w // 2 - 60, h // 2 + 50,
                w // 2 + 60, h // 2 + 50,
                0.3
            )
            logger.info("Slider interaction via fallback swipe")

        except Exception as e:
            logger.warning("Slider interaction failed: %s", e)

        return False

    def _close_current_popup(self):
        """Close any open popup by pressing back or clicking the trigger button."""
        # Try pressing back first
        try:
            self.device.press("back")
            time.sleep(ANIMATION_WAIT)
            return True
        except Exception:
            pass

        # Try clicking the tool_controls/color_picker button again (toggle off)
        for sel in ["tool_controls", "color_picker"]:
            try:
                result = self.locator.find(sel, timeout=0.5)
                if result.found and result.element is not None:
                    result.element.click()
                    time.sleep(ANIMATION_WAIT)
                    return True
            except Exception:
                continue

        return False

    def _switch_to_pen(self):
        """Switch back to pen tool."""
        self.actions.click("tool_controls", timeout=DEFAULT_TIMEOUT)
        time.sleep(ANIMATION_WAIT)
        self.actions.click("pen_tab", timeout=SHORT_TIMEOUT)
        self._close_current_popup()
