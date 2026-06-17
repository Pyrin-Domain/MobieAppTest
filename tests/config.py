# -*- coding: utf-8 -*-
"""
DrawAnywhere GUI Automation Test Suite - Configuration
=======================================================
Central configuration for all test parameters, selectors, and device settings.

Key design decisions:
- All timeouts are centralized for easy tuning
- Multi-language selectors using regex to handle both EN and ZH locales
- Device serial can be set via environment variable DEVICE_SERIAL or auto-detected
"""

import os
import re
from pathlib import Path

# ── Project Paths ───────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = Path(__file__).resolve().parent
SCREENSHOT_DIR = TEST_DIR / "screenshots"
REPORT_DIR = TEST_DIR / "reports"
LOG_DIR = TEST_DIR / "logs"

# Ensure directories exist
for d in [SCREENSHOT_DIR, REPORT_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Device Configuration ────────────────────────────────────────────────────
DEVICE_SERIAL = os.environ.get("DEVICE_SERIAL", None)  # None = auto-detect first device
PACKAGE_NAME = "com.shezik.drawanywhere"
ACTIVITY_MAIN = ".MainActivity"

# ── Timeout Configuration (seconds) ─────────────────────────────────────────
DEFAULT_TIMEOUT = 15          # Default wait for element visibility
SHORT_TIMEOUT = 5             # Quick operations (button click response)
LONG_TIMEOUT = 30             # App startup, complex animations
POPUP_TIMEOUT = 0.5           # Quick check for popup existence (fast with native selectors)
IDLE_TIMEOUT = 2              # Short pause after actions
ANIMATION_WAIT = 1.5          # Wait for Compose animations to settle

# ── Retry Configuration ─────────────────────────────────────────────────────
MAX_RETRIES = 3               # Max retries for critical operations
RETRY_DELAY = 1.0             # Delay between retries (seconds)

# ── Drawing Configuration ───────────────────────────────────────────────────
DRAW_STROKE_STEPS = 20        # Steps in a simulated drawing stroke
DRAW_STROKE_DURATION = 0.5    # Duration of a simulated stroke (seconds)

# ── Screenshot Configuration ─────────────────────────────────────────────────
SCREENSHOT_ON_FAILURE = True
SCREENSHOT_ON_STEP = False    # Set True to capture every step (debug mode)
SCREENSHOT_FORMAT = "png"

# ── Multi-Language Selectors ────────────────────────────────────────────────
# Each selector has:
#   - desc_regex:  regex matching content-description (primary strategy)
#   - text_regex:  regex matching text (fallback strategy)
#   - class_name:  expected Android class name
#   - xpath:       explicit XPath (last resort)

SELECTORS = {
    # ── Toolbar Primary Buttons (always visible) ─────────────────────────
    "visibility": {
        "desc_regex": re.compile(
            r"(Hide canvas|Show canvas|隐藏画布|显示画布)", re.IGNORECASE
        ),
        "desc_en": ["Hide canvas", "Show canvas"],
        "desc_zh": ["隐藏画布", "显示画布"],
        "hint": "Toggle canvas visibility button",
    },
    "undo": {
        "desc_regex": re.compile(r"(Undo|撤销)", re.IGNORECASE),
        "desc_en": ["Undo"],
        "desc_zh": ["撤销"],
        "hint": "Undo last stroke button",
    },
    "clear": {
        "desc_regex": re.compile(r"(Clear canvas|清空画布)", re.IGNORECASE),
        "desc_en": ["Clear canvas"],
        "desc_zh": ["清空画布"],
        "hint": "Clear all paths button",
    },
    "tool_controls": {
        "desc_regex": re.compile(r"(Tool controls|工具选项)", re.IGNORECASE),
        "desc_en": ["Tool controls"],
        "desc_zh": ["工具选项"],
        "hint": "Tool controls popup button (pen type, width, opacity)",
    },
    "color_picker": {
        "desc_regex": re.compile(r"(Color picker|取色器)", re.IGNORECASE),
        "desc_en": ["Color picker"],
        "desc_zh": ["取色器"],
        "hint": "Color picker popup button",
    },

    # ── Toolbar Secondary Buttons (in expandable drawer) ──────────────────
    "passthrough": {
        "desc_regex": re.compile(
            r"(Enable passthrough|Disable passthrough|启用触摸透传|禁用触摸透传)",
            re.IGNORECASE
        ),
        "desc_en": ["Enable passthrough", "Disable passthrough"],
        "desc_zh": ["启用触摸透传", "禁用触摸透传"],
        "hint": "Toggle touch passthrough button",
    },
    "redo": {
        "desc_regex": re.compile(r"(Redo|重做)", re.IGNORECASE),
        "desc_en": ["Redo"],
        "desc_zh": ["重做"],
        "hint": "Redo button",
    },
    "settings": {
        "desc_regex": re.compile(r"(Settings|设置)", re.IGNORECASE),
        "desc_en": ["Settings"],
        "desc_zh": ["设置"],
        "hint": "Settings popup button",
    },
    "expand_toolbar": {
        "desc_regex": re.compile(r"(Expand toolbar|展开工具栏)", re.IGNORECASE),
        "desc_en": ["Expand toolbar"],
        "desc_zh": ["展开工具栏"],
        "hint": "Expand secondary drawer button",
    },
    "collapse_toolbar": {
        "desc_regex": re.compile(r"(Collapse toolbar|收起工具栏)", re.IGNORECASE),
        "desc_en": ["Collapse toolbar"],
        "desc_zh": ["收起工具栏"],
        "hint": "Collapse secondary drawer button",
    },

    # ── Popup Content Controls ────────────────────────────────────────────
    "pen_tab": {
        "text_regex": re.compile(r"(Pen|笔)", re.IGNORECASE),
        "hint": "Pen tool button in popup",
    },
    "eraser_tab": {
        "text_regex": re.compile(r"(Stroke Eraser|笔画橡皮)", re.IGNORECASE),
        "hint": "Stroke eraser button in popup",
    },
    "tools_label": {
        "text_regex": re.compile(r"(Tools|工具)", re.IGNORECASE),
        "hint": "Tools section label",
    },
    "color_label": {
        "text_regex": re.compile(r"(Color|颜色)", re.IGNORECASE),
        "hint": "Color section label",
    },
    "width_label": {
        "text_regex": re.compile(r"(Width|宽度)", re.IGNORECASE),
        "hint": "Stroke width label",
    },
    "opacity_label": {
        "text_regex": re.compile(r"(Opacity|不透明度)", re.IGNORECASE),
        "hint": "Stroke opacity label",
    },
    "horizontal_btn": {
        "text_regex": re.compile(r"(Horizontal|横向)", re.IGNORECASE),
        "hint": "Horizontal orientation button",
    },
    "vertical_btn": {
        "text_regex": re.compile(r"(Vertical|竖向)", re.IGNORECASE),
        "hint": "Vertical orientation button",
    },
    "clear_on_hide_checkbox": {
        "text_regex": re.compile(r"(Clear on hiding canvas|隐藏画布时清空)", re.IGNORECASE),
        "hint": "Auto-clear checkbox label",
    },
    "visible_on_start_checkbox": {
        "text_regex": re.compile(r"(Canvas visible on start|启动时显示画布)", re.IGNORECASE),
        "hint": "Visible-on-start checkbox label",
    },
    "quit_btn": {
        "text_regex": re.compile(r"(Quit|退出)", re.IGNORECASE),
        "hint": "Quit application button",
    },
    "settings_label": {
        "text_regex": re.compile(r"(Settings|设置)", re.IGNORECASE),
        "hint": "Settings section label in popup",
    },

    # ── Permission Dialog ─────────────────────────────────────────────────
    "permission_dialog_title": {
        "text_regex": re.compile(r"(Permission Required|需要权限)", re.IGNORECASE),
        "hint": "Overlay permission dialog title",
    },
    "permission_accept": {
        "text_regex": re.compile(r"(Proceed|继续)", re.IGNORECASE),
        "hint": "Accept permission button",
    },
    "permission_deny": {
        "text_regex": re.compile(r"(Exit|退出)", re.IGNORECASE),
        "hint": "Deny permission button",
    },

    # ── System Popups (generic) ───────────────────────────────────────────
    "system_allow": {
        "text_regex": re.compile(
            r"(Allow|允许|Always|始终|While using|使用时)", re.IGNORECASE
        ),
        "resource_id": "android:id/button1",
        "hint": "Generic system Allow/OK button",
    },
    "system_deny": {
        "text_regex": re.compile(r"(Deny|拒绝|Cancel|取消)", re.IGNORECASE),
        "resource_id": "android:id/button2",
        "hint": "Generic system Deny/Cancel button",
    },
    "system_confirm": {
        "text_regex": re.compile(r"(OK|确定|Yes|是|Allow|允许)", re.IGNORECASE),
        "hint": "Generic confirmation button",
    },

    # ── App Name ──────────────────────────────────────────────────────────
    "app_name": {
        "text_regex": re.compile(r"DrawAnywhere", re.IGNORECASE),
        "hint": "App name text",
    },
}

# ── Selector Priority Strategies ────────────────────────────────────────────
# Order in which locator strategies are tried for each element
STRATEGY_ORDER = [
    "description",       # content-desc (most reliable for Compose)
    "description_contains",
    "text",              # visible text
    "text_contains",
    "class_desc",        # className + description combo
    "class_text",        # className + text combo
    "xpath",             # explicit XPath
    "coordinate_fallback",  # last resort: estimated coordinates
]

# ── Logging Configuration ───────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
)
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ── Report Configuration ────────────────────────────────────────────────────
REPORT_TITLE = "DrawAnywhere GUI Automation Test Report"
REPORT_DESCRIPTION = "UIAutomator2-based automated GUI tests for DrawAnywhere"
