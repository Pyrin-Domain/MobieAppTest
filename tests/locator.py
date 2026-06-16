# -*- coding: utf-8 -*-
"""
DrawAnywhere GUI Automation - Multi-Strategy Element Locator
=============================================================
Core locator module implementing intelligent, multi-strategy element finding
for Jetpack Compose UIs (which lack traditional Android resource IDs).

Key features:
- Multi-strategy fallback: description → text → className+desc → XPath → coordinates
- Smart waiting with configurable timeout (replaces fixed sleep)
- Automatic retry on ElementNotFoundError (2-3 retries)
- Comprehensive logging of every locator attempt
- Dump UI hierarchy on failure for debugging
- Screen-relative coordinate calculations (no hardcoded positions)
"""

from __future__ import annotations

import functools
import logging
import re
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import uiautomator2 as u2

from config import (
    DEFAULT_TIMEOUT,
    SHORT_TIMEOUT,
    LONG_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
    SCREENSHOT_DIR,
    SELECTORS,
    STRATEGY_ORDER,
    SCREENSHOT_ON_FAILURE,
    SCREENSHOT_FORMAT,
)

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Data Classes
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class LocatorResult:
    """Result of an element location attempt."""
    element: Optional[Any] = None          # uiautomator2 element object
    strategy_used: str = ""                # Which strategy succeeded
    attempts: int = 0                      # Number of attempts made
    elapsed_ms: float = 0.0                # Time taken to locate
    found: bool = False                    # Whether element was found
    info: Dict[str, Any] = field(default_factory=dict)  # Extra debug info


@dataclass
class LocateCriteria:
    """Flexible criteria for locating an element."""
    desc: Optional[str] = None             # Exact content-description
    desc_regex: Optional[re.Pattern] = None  # Regex for content-description
    desc_contains: Optional[str] = None    # Substring in content-description
    text: Optional[str] = None             # Exact text
    text_regex: Optional[re.Pattern] = None  # Regex for text
    text_contains: Optional[str] = None    # Substring in text
    class_name: Optional[str] = None       # Android class name
    resource_id: Optional[str] = None      # Android resource ID
    xpath: Optional[str] = None            # XPath expression
    index: Optional[int] = None            # Element index among siblings
    clickable: Optional[bool] = None       # Must be clickable
    enabled: Optional[bool] = None         # Must be enabled
    bounds_hint: Optional[Tuple[float, float, float, float]] = None  # (x1,y1,x2,y2) relative


# ────────────────────────────────────────────────────────────────────────────
# Helper Utilities
# ────────────────────────────────────────────────────────────────────────────

def _retry_on_failure(max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY):
    """Decorator: retry a function on uiautomator2 exceptions."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs, _attempt=attempt)
                except (TimeoutError, RuntimeError) as e:
                    last_exc = e
                    if attempt < max_retries:
                        logger.warning(
                            "Retry %d/%d for %s: %s",
                            attempt, max_retries, func.__name__, e
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "All %d retries exhausted for %s: %s",
                            max_retries, func.__name__, e
                        )
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator


def _dump_hierarchy(device: u2.Device, tag: str = "") -> Optional[str]:
    """Dump current UI hierarchy to string for debugging."""
    try:
        xml = device.dump_hierarchy()
        if tag:
            logger.debug("[%s] UI hierarchy dumped (%d chars)", tag, len(xml))
        return xml
    except Exception as e:
        logger.error("Failed to dump UI hierarchy: %s", e)
        return None


def _take_screenshot(device: u2.Device, name: str = "debug") -> Optional[Path]:
    """Take a screenshot for debugging."""
    try:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.{SCREENSHOT_FORMAT}"
        filepath = SCREENSHOT_DIR / filename
        device.screenshot(str(filepath))
        logger.info("Screenshot saved: %s", filepath)
        return filepath
    except Exception as e:
        logger.error("Failed to take screenshot: %s", e)
        return None


# ────────────────────────────────────────────────────────────────────────────
# Core Locator Class
# ────────────────────────────────────────────────────────────────────────────

class ElementLocator:
    """
    Multi-strategy element locator for Jetpack Compose UIs.

    Implements an intelligent fallback chain:
      1. content-desc (exact match)
      2. content-desc (regex / contains)
      3. text (exact match)
      4. text (regex / contains)
      5. className + description combo
      6. className + text combo
      7. XPath
      8. Coordinate estimation (last resort)

    Usage:
        locator = ElementLocator(device)
        result = locator.find("visibility", timeout=10)
        if result.found:
            result.element.click()
    """

    def __init__(self, device: u2.Device):
        self.device = device
        self._screenshot_counter = 0

    # ── Public API ────────────────────────────────────────────────────────

    def find(
        self,
        name_or_criteria: Union[str, LocateCriteria],
        timeout: float = DEFAULT_TIMEOUT,
        raise_on_fail: bool = False,
    ) -> LocatorResult:
        """
        Find an element using multi-strategy fallback.

        Args:
            name_or_criteria: Either a selector name from config.SELECTORS,
                              or a LocateCriteria object.
            timeout: Maximum time to wait for the element (seconds).
            raise_on_fail: If True, raise TimeoutError when not found.

        Returns:
            LocatorResult with found status, element reference, and debug info.
        """
        # Resolve criteria from name or direct object
        if isinstance(name_or_criteria, str):
            criteria = self._resolve_selector(name_or_criteria)
        else:
            criteria = name_or_criteria

        if criteria is None:
            msg = f"No criteria available for '{name_or_criteria}'"
            logger.error(msg)
            if raise_on_fail:
                raise ValueError(msg)
            return LocatorResult(found=False, info={"error": msg})

        start_time = time.monotonic()
        last_result: Optional[LocatorResult] = None

        for strategy in self._get_strategies(criteria):
            logger.debug(
                "Trying strategy '%s' for criteria (desc=%s, text=%s, class=%s)...",
                strategy, criteria.desc, criteria.text, criteria.class_name
            )
            try:
                result = self._execute_strategy(criteria, strategy, timeout - (time.monotonic() - start_time))
                if result.found:
                    result.elapsed_ms = (time.monotonic() - start_time) * 1000
                    logger.info(
                        "✓ Found element via '%s' strategy in %.0fms (attempts=%d)",
                        result.strategy_used, result.elapsed_ms, result.attempts
                    )
                    return result
                last_result = result
            except Exception as e:
                logger.debug("Strategy '%s' failed: %s", strategy, e)
                last_result = LocatorResult(
                    found=False,
                    strategy_used=strategy,
                    info={"error": str(e)}
                )

            # Check if we're out of time
            if time.monotonic() - start_time > timeout:
                break

        # All strategies failed
        elapsed = (time.monotonic() - start_time) * 1000
        logger.error(
            "✗ Element NOT found after %.0fms (all strategies exhausted)",
            elapsed
        )

        # Debug: dump hierarchy and screenshot
        if SCREENSHOT_ON_FAILURE:
            tag = name_or_criteria if isinstance(name_or_criteria, str) else "element"
            _take_screenshot(self.device, f"locate_failed_{tag}")
            _dump_hierarchy(self.device, tag)

        if raise_on_fail:
            raise TimeoutError(
                f"Element not found after {elapsed:.0f}ms. "
                f"Criteria: desc={criteria.desc}, text={criteria.text}, "
                f"class={criteria.class_name}"
            )

        result = last_result or LocatorResult(found=False)
        result.elapsed_ms = elapsed
        return result

    def wait_for(
        self,
        name_or_criteria: Union[str, LocateCriteria],
        timeout: float = DEFAULT_TIMEOUT,
        state: str = "exists",  # "exists" | "clickable" | "enabled" | "gone"
    ) -> LocatorResult:
        """
        Smart wait: block until element reaches desired state.

        Args:
            name_or_criteria: Selector name or LocateCriteria.
            timeout: Max wait time.
            state: Target state:
                - "exists": element is present in hierarchy
                - "clickable": element is present AND clickable
                - "enabled": element is present AND enabled
                - "gone": element DISAPPEARS from hierarchy

        Returns:
            LocatorResult.
        """
        if state == "gone":
            return self._wait_until_gone(name_or_criteria, timeout)

        criteria = (
            name_or_criteria if isinstance(name_or_criteria, LocateCriteria)
            else self._resolve_selector(name_or_criteria)
        )
        if criteria is None:
            return LocatorResult(found=False, info={"error": "No criteria"})

        start = time.monotonic()
        deadline = start + timeout
        poll_interval = 0.3

        while time.monotonic() < deadline:
            result = self.find(criteria, timeout=1.0)
            if result.found and result.element is not None:
                el = result.element
                if state == "exists":
                    result.elapsed_ms = (time.monotonic() - start) * 1000
                    return result
                if state == "clickable":
                    try:
                        if el.info.get("clickable", False):
                            result.elapsed_ms = (time.monotonic() - start) * 1000
                            return result
                    except Exception:
                        pass
                if state == "enabled":
                    try:
                        if el.info.get("enabled", False):
                            result.elapsed_ms = (time.monotonic() - start) * 1000
                            return result
                    except Exception:
                        pass
            time.sleep(poll_interval)

        elapsed = (time.monotonic() - start) * 1000
        logger.error("wait_for(state=%s) timed out after %.0fms", state, elapsed)
        return LocatorResult(found=False, elapsed_ms=elapsed)

    def exists(self, name_or_criteria: Union[str, LocateCriteria], timeout: float = SHORT_TIMEOUT) -> bool:
        """Quick check if element exists."""
        result = self.find(name_or_criteria, timeout=timeout)
        return result.found

    def get_text(self, name_or_criteria: Union[str, LocateCriteria], timeout: float = DEFAULT_TIMEOUT) -> Optional[str]:
        """Find element and return its text."""
        result = self.find(name_or_criteria, timeout=timeout)
        if result.found and result.element is not None:
            try:
                return result.element.get_text()
            except Exception as e:
                logger.warning("Could not get text: %s", e)
        return None

    def get_bounds(self, name_or_criteria: Union[str, LocateCriteria], timeout: float = DEFAULT_TIMEOUT) -> Optional[Tuple[int, int, int, int]]:
        """Find element and return its bounds (left, top, right, bottom)."""
        result = self.find(name_or_criteria, timeout=timeout)
        if result.found and result.element is not None:
            try:
                return result.element.bounds()
            except Exception as e:
                logger.warning("Could not get bounds: %s", e)
        return None

    # ── Strategy Resolution ───────────────────────────────────────────────

    def _resolve_selector(self, name: str) -> Optional[LocateCriteria]:
        """Convert a named selector from config to LocateCriteria."""
        selector = SELECTORS.get(name)
        if selector is None:
            logger.error("Unknown selector name: '%s'. Available: %s", name, list(SELECTORS.keys()))
            return None

        return LocateCriteria(
            desc=selector.get("desc"),
            desc_regex=selector.get("desc_regex"),
            text_regex=selector.get("text_regex"),
            resource_id=selector.get("resource_id"),
            class_name=selector.get("class_name"),
            xpath=selector.get("xpath"),
        )

    def _get_strategies(self, criteria: LocateCriteria) -> List[str]:
        """Determine which strategies to try based on available criteria."""
        strategies = []

        # Build strategies based on what criteria we have
        if criteria.desc or criteria.desc_regex or criteria.desc_contains:
            strategies.append("description")
            strategies.append("description_contains")
        if criteria.text or criteria.text_regex or criteria.text_contains:
            strategies.append("text")
            strategies.append("text_contains")
        if criteria.class_name:
            if criteria.desc or criteria.desc_regex or criteria.desc_contains:
                strategies.append("class_desc")
            if criteria.text or criteria.text_regex or criteria.text_contains:
                strategies.append("class_text")
        if criteria.xpath:
            strategies.append("xpath")
        if criteria.resource_id:
            strategies.append("resource_id")

        # Always add coordinate fallback as last resort
        strategies.append("coordinate_fallback")

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for s in strategies:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        return unique

    # ── Strategy Execution ─────────────────────────────────────────────────

    def _execute_strategy(
        self,
        criteria: LocateCriteria,
        strategy: str,
        timeout: float,
    ) -> LocatorResult:
        """Execute a single location strategy."""
        timeout = max(timeout, 0.5)  # Minimum timeout

        if strategy == "description":
            return self._find_by_description(criteria, timeout, exact=True)
        elif strategy == "description_contains":
            return self._find_by_description(criteria, timeout, exact=False)
        elif strategy == "text":
            return self._find_by_text(criteria, timeout, exact=True)
        elif strategy == "text_contains":
            return self._find_by_text(criteria, timeout, exact=False)
        elif strategy == "class_desc":
            return self._find_by_class_and_desc(criteria, timeout)
        elif strategy == "class_text":
            return self._find_by_class_and_text(criteria, timeout)
        elif strategy == "xpath":
            return self._find_by_xpath(criteria, timeout)
        elif strategy == "resource_id":
            return self._find_by_resource_id(criteria, timeout)
        elif strategy == "coordinate_fallback":
            return self._find_by_coordinates(criteria)
        else:
            return LocatorResult(found=False, strategy_used=strategy,
                                 info={"error": f"Unknown strategy: {strategy}"})

    # ── Strategy: Description (content-desc) ──────────────────────────────

    def _find_by_description(
        self, criteria: LocateCriteria, timeout: float, exact: bool = True
    ) -> LocatorResult:
        """Find by content-description."""
        desc = criteria.desc
        pattern = criteria.desc_regex
        contains = criteria.desc_contains

        try:
            if desc and exact:
                el = self.device(description=desc)
            elif desc and not exact:
                el = self.device(descriptionContains=desc)
            elif pattern:
                # uiautomator2 doesn't support regex natively; iterate matches
                el = self._find_by_description_regex(pattern, timeout)
                if el is not None:
                    return LocatorResult(
                        element=el, strategy_used="description(regex)",
                        attempts=1, found=True
                    )
                return LocatorResult(found=False, strategy_used="description(regex)")
            elif contains:
                el = self.device(descriptionContains=contains)
            else:
                return LocatorResult(found=False, strategy_used="description")

            if el.wait(timeout=timeout):
                return LocatorResult(
                    element=el, strategy_used="description",
                    attempts=1, found=True
                )
        except Exception as e:
            logger.debug("Description strategy error: %s", e)

        return LocatorResult(found=False, strategy_used="description")

    def _find_by_description_regex(self, pattern: re.Pattern, timeout: float):
        """Find element whose content-description matches a regex."""
        # Fast path: use native uiautomator2 descriptionMatches (no XML dump)
        try:
            el = self.device(descriptionMatches=pattern.pattern)
            if el.wait(timeout=timeout):
                return el
        except Exception:
            pass

        # Fallback: XML-based search
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                xml = self.device.dump_hierarchy()
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml)
                for node in root.iter("node"):
                    desc = node.get("content-desc", "")
                    if desc and pattern.search(desc):
                        bounds = node.get("bounds", "")
                        if bounds:
                            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
                            if m:
                                x1, y1, x2, y2 = map(int, m.groups())
                                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                                try:
                                    el = self.device(description=desc)
                                    if el.exists:
                                        return el
                                except Exception:
                                    pass
                                break
            except Exception:
                pass
            time.sleep(0.5)
        return None

    # ── Strategy: Text ────────────────────────────────────────────────────

    def _find_by_text(
        self, criteria: LocateCriteria, timeout: float, exact: bool = True
    ) -> LocatorResult:
        """Find by text content."""
        text = criteria.text
        pattern = criteria.text_regex
        contains = criteria.text_contains

        try:
            if text and exact:
                el = self.device(text=text)
            elif text and not exact:
                el = self.device(textContains=text)
            elif pattern:
                return self._find_by_text_regex(pattern, timeout)
            elif contains:
                el = self.device(textContains=contains)
            else:
                return LocatorResult(found=False, strategy_used="text")

            if el.wait(timeout=timeout):
                return LocatorResult(
                    element=el, strategy_used="text",
                    attempts=1, found=True
                )
        except Exception as e:
            logger.debug("Text strategy error: %s", e)

        return LocatorResult(found=False, strategy_used="text")

    def _find_by_text_regex(self, pattern: re.Pattern, timeout: float) -> LocatorResult:
        """Find element whose text matches a regex."""
        # Fast path: use native uiautomator2 textMatches (no XML dump)
        try:
            el = self.device(textMatches=pattern.pattern)
            if el.wait(timeout=timeout):
                return LocatorResult(
                    element=el, strategy_used="text(regex)",
                    attempts=1, found=True
                )
        except Exception:
            pass

        # Fallback: XML-based search
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                xml = self.device.dump_hierarchy()
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml)
                for node in root.iter("node"):
                    node_text = node.get("text", "")
                    if node_text and pattern.search(node_text):
                        try:
                            el = self.device(text=node_text)
                            if el.exists:
                                return LocatorResult(
                                    element=el, strategy_used="text(regex)",
                                    attempts=1, found=True
                                )
                        except Exception:
                            pass
            except Exception:
                pass
            time.sleep(0.5)
        return LocatorResult(found=False, strategy_used="text(regex)")

    # ── Strategy: className + Description ─────────────────────────────────

    def _find_by_class_and_desc(self, criteria: LocateCriteria, timeout: float) -> LocatorResult:
        """Find by className combined with content-description."""
        class_name = criteria.class_name
        desc = criteria.desc
        pattern = criteria.desc_regex
        contains = criteria.desc_contains

        if not class_name:
            return LocatorResult(found=False, strategy_used="class_desc")

        try:
            el = self.device(className=class_name)
            if not el.wait(timeout=timeout):
                return LocatorResult(found=False, strategy_used="class_desc")

            # Now filter by description
            for child in self._iter_children(el):
                try:
                    child_desc = child.info.get("contentDescription", "")
                    if desc and child_desc == desc:
                        return LocatorResult(element=child, strategy_used="class_desc", attempts=1, found=True)
                    if pattern and pattern.search(child_desc):
                        return LocatorResult(element=child, strategy_used="class_desc(regex)", attempts=1, found=True)
                    if contains and contains in child_desc:
                        return LocatorResult(element=child, strategy_used="class_desc(contains)", attempts=1, found=True)
                except Exception:
                    continue
        except Exception as e:
            logger.debug("class_desc strategy error: %s", e)

        return LocatorResult(found=False, strategy_used="class_desc")

    def _find_by_class_and_text(self, criteria: LocateCriteria, timeout: float) -> LocatorResult:
        """Find by className combined with text."""
        class_name = criteria.class_name
        text = criteria.text
        pattern = criteria.text_regex
        contains = criteria.text_contains

        if not class_name:
            return LocatorResult(found=False, strategy_used="class_text")

        try:
            el = self.device(className=class_name)
            if not el.wait(timeout=timeout):
                return LocatorResult(found=False, strategy_used="class_text")

            for child in self._iter_children(el):
                try:
                    child_text = child.info.get("text", "")
                    if text and child_text == text:
                        return LocatorResult(element=child, strategy_used="class_text", attempts=1, found=True)
                    if pattern and pattern.search(child_text):
                        return LocatorResult(element=child, strategy_used="class_text(regex)", attempts=1, found=True)
                    if contains and contains in child_text:
                        return LocatorResult(element=child, strategy_used="class_text(contains)", attempts=1, found=True)
                except Exception:
                    continue
        except Exception as e:
            logger.debug("class_text strategy error: %s", e)

        return LocatorResult(found=False, strategy_used="class_text")

    # ── Strategy: XPath ───────────────────────────────────────────────────

    def _find_by_xpath(self, criteria: LocateCriteria, timeout: float) -> LocatorResult:
        """Find using XPath expression."""
        xpath = criteria.xpath
        if not xpath:
            return LocatorResult(found=False, strategy_used="xpath")

        try:
            el = self.device.xpath(xpath)
            if el.wait(timeout=timeout):
                return LocatorResult(
                    element=el, strategy_used="xpath",
                    attempts=1, found=True
                )
        except Exception as e:
            logger.debug("XPath strategy error: %s", e)

        return LocatorResult(found=False, strategy_used="xpath")

    # ── Strategy: Resource ID ─────────────────────────────────────────────

    def _find_by_resource_id(self, criteria: LocateCriteria, timeout: float) -> LocatorResult:
        """Find by Android resource ID."""
        rid = criteria.resource_id
        if not rid:
            return LocatorResult(found=False, strategy_used="resource_id")

        try:
            el = self.device(resourceId=rid)
            if el.wait(timeout=timeout):
                return LocatorResult(
                    element=el, strategy_used="resource_id",
                    attempts=1, found=True
                )
        except Exception as e:
            logger.debug("resource_id strategy error: %s", e)

        return LocatorResult(found=False, strategy_used="resource_id")

    # ── Strategy: Coordinate Fallback ─────────────────────────────────────

    def _find_by_coordinates(self, criteria: LocateCriteria) -> LocatorResult:
        """
        Last-resort strategy: estimate element position from screen dimensions.

        This parses the UI hierarchy to find any matching element and uses its
        bounds. If absolutely nothing matches, returns failure.
        """
        logger.warning("Using coordinate fallback strategy (last resort)")

        try:
            xml = self.device.dump_hierarchy()
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml)

            # Try to find ANY node matching our criteria in the hierarchy
            desc_pattern = criteria.desc_regex
            text_pattern = criteria.text_regex
            desc = criteria.desc
            text = criteria.text
            contains_desc = criteria.desc_contains
            contains_text = criteria.text_contains

            matches = []
            for node in root.iter("node"):
                node_desc = node.get("content-desc", "")
                node_text = node.get("text", "")
                node_class = node.get("class", "")
                bounds_str = node.get("bounds", "")
                clickable = node.get("clickable", "false") == "true"

                matched = False
                if desc and node_desc == desc:
                    matched = True
                elif desc_pattern and desc_pattern.search(node_desc):
                    matched = True
                elif contains_desc and contains_desc in node_desc:
                    matched = True
                elif text and node_text == text:
                    matched = True
                elif text_pattern and text_pattern.search(node_text):
                    matched = True
                elif contains_text and contains_text in node_text:
                    matched = True
                elif criteria.class_name and criteria.class_name in node_class:
                    matched = True

                if matched and clickable and bounds_str:
                    matches.append((node, bounds_str))

            # Prefer clickable matches; fall back to any match
            if not matches:
                for node in root.iter("node"):
                    node_desc = node.get("content-desc", "")
                    node_text = node.get("text", "")
                    bounds_str = node.get("bounds", "")
                    if bounds_str and ((desc_pattern and desc_pattern.search(node_desc)) or
                                       (text_pattern and text_pattern.search(node_text))):
                        matches.append((node, bounds_str))

            if matches:
                node, bounds_str = matches[0]
                m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
                if m:
                    x1, y1, x2, y2 = map(int, m.groups())
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    logger.info(
                        "Coordinate fallback: found match at (%d, %d), bounds=%s, desc=%s, text=%s",
                        cx, cy, bounds_str, node.get("content-desc", ""), node.get("text", "")
                    )
                    return LocatorResult(
                        element=None,  # No element object but we have coordinates
                        strategy_used="coordinate_fallback",
                        attempts=1, found=True,
                        info={"coords": (cx, cy), "bounds": (x1, y1, x2, y2)}
                    )
        except Exception as e:
            logger.error("Coordinate fallback failed: %s", e)

        return LocatorResult(found=False, strategy_used="coordinate_fallback")

    # ── Wait Until Gone ───────────────────────────────────────────────────

    def _wait_until_gone(
        self, name_or_criteria: Union[str, LocateCriteria], timeout: float
    ) -> LocatorResult:
        """Wait for an element to disappear from the hierarchy."""
        if isinstance(name_or_criteria, str):
            criteria = self._resolve_selector(name_or_criteria)
        else:
            criteria = name_or_criteria

        if criteria is None:
            return LocatorResult(found=False, info={"error": "No criteria"})

        start = time.monotonic()
        deadline = start + timeout

        while time.monotonic() < deadline:
            result = self.find(criteria, timeout=1.0)
            if not result.found:
                elapsed = (time.monotonic() - start) * 1000
                logger.info("Element is now gone (after %.0fms)", elapsed)
                return LocatorResult(found=True, elapsed_ms=elapsed, info={"state": "gone"})
            time.sleep(0.3)

        elapsed = (time.monotonic() - start) * 1000
        logger.warning("Element did NOT disappear within %.0fms", elapsed)
        return LocatorResult(found=False, elapsed_ms=elapsed, info={"state": "still_present"})

    # ── Iterator Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _iter_children(parent_element):
        """Iterate child elements (if count is reasonable)."""
        try:
            count = parent_element.count()
            if count > 200:
                # Too many children; avoid iterating
                return
            for i in range(min(count, 100)):
                try:
                    yield parent_element.child(i)
                except Exception:
                    break
        except Exception:
            pass


# ────────────────────────────────────────────────────────────────────────────
# Module-level convenience function
# ────────────────────────────────────────────────────────────────────────────

def create_locator(device: u2.Device) -> ElementLocator:
    """Create an ElementLocator instance for the given device."""
    return ElementLocator(device)
