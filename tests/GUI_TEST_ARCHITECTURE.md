# DrawAnywhere GUI Automation Test — Architecture & Design

> **Framework**: Python + UIAutomator2  
> **Target**: Jetpack Compose Android App (no traditional resource IDs)  
> **Test Modules**: `launch` / `drawing`  
> **Last Updated**: 2026-06-16

---

## 1. Architecture Overview

The test suite follows a layered architecture:

```
┌──────────────────────────────────────────────────────┐
│                   test_runner.py                      │  ← CLI entry, orchestration
├──────────────────────────────────────────────────────┤
│  test_launch.py          test_drawing.py              │  ← Test case modules
├──────────────────────────────────────────────────────┤
│                    base_test.py                        │  ← Shared lifecycle, step tracking
├────────────────────────┬─────────────────────────────┤
│     actions.py          │       locator.py             │  ← Core engine
│  (click/swipe/draw/     │  (multi-strategy element     │
│   popup handling)       │   finding for Compose)       │
├────────────────────────┴─────────────────────────────┤
│                    config.py                           │  ← All timeouts, selectors, paths
├──────────────────────────────────────────────────────┤
│                    report.py                           │  ← HTML / JSON / console output
└──────────────────────────────────────────────────────┘
```

Every test module inherits from `BaseTest`, which provides automatic device connection, logging, screenshot capture, and per-step result tracking.

---

## 2. Configuration System (`config.py`)

All parameters are centralized in one file — no magic numbers scattered across test code.

### 2.1 Timeout Hierarchy

The suite uses a **layered timeout strategy** to balance reliability and speed:

| Constant | Default | Purpose |
|---|---|---|
| `DEFAULT_TIMEOUT` | **15s** | Standard wait for element visibility |
| `SHORT_TIMEOUT` | **5s** | Quick operations (button click response, existence check) |
| `LONG_TIMEOUT` | **30s** | App startup, complex animations, permission flow |
| `POPUP_TIMEOUT` | **1s** | Quick check for popup existence (uses fast native selectors, not XML dumps) |
| `IDLE_TIMEOUT` | **2s** | Pause after actions for UI to settle |
| `ANIMATION_WAIT` | **1.5s** | Wait for Compose animations to complete |
| `RETRY_DELAY` | **1.0s** | Delay between retry attempts |
| `MAX_RETRIES` | **3** | Max retries for critical operations |

**Design rationale**: The timeout stack prevents the common "flaky test" problem:
- **Short timeouts** for elements that should appear quickly (button responses)
- **Long timeouts** for app-level operations (cold start, permission grant flow)
- **Adaptive retries** — retry with backoff instead of immediately failing

### 2.2 Drawing Simulation

```
DRAW_STROKE_STEPS    = 20          # Intermediate touch points for smooth strokes
DRAW_STROKE_DURATION = 0.5s        # Total stroke time (realistic human-like drawing)
```

### 2.3 Multi-Language Selectors

Every UI element is defined with **regex-based bilingual patterns** (English + Chinese):

```python
"visibility": {
    "desc_regex": re.compile(
        r"(Hide canvas|Show canvas|隐藏画布|显示画布)", re.IGNORECASE
    ),
}
```

This ensures the same test suite works on both English and Chinese device locales without modification.

### 2.4 Screenshot & Reporting

- `SCREENSHOT_ON_FAILURE = True` — automatic screenshot on every failed step
- `SCREENSHOT_ON_STEP = False` — optional per-step capture for debug mode
- All screenshots go to `tests/screenshots/`
- Reports go to `tests/reports/` (HTML + JSON)

---

## 3. Multi-Strategy Element Locator (`locator.py`)

> **This is the core innovation of the test suite.**

### 3.1 The Problem

Jetpack Compose UIs do **not** expose traditional Android resource IDs (`android:id/...`). Instead, elements are described by:

- `contentDescription` (accessibility label)
- `text` (visible text)
- `className` (e.g., `android.widget.ImageButton`)
- Layout bounds (pixel coordinates)

Standard `findElementById()` is **useless** for Compose UIs.

### 3.2 The Solution: 8-Strategy Fallback Chain

`ElementLocator.find()` tries strategies in order, stopping at the first success:

| # | Strategy | Description |
|---|---|---|
| 1 | **description** (exact) | Match `contentDescription` exactly |
| 2 | **description_contains** | Substring / regex match on `contentDescription` |
| 3 | **text** (exact) | Match visible text exactly |
| 4 | **text_contains** | Substring / regex match on text |
| 5 | **class_desc** | Filter by `className` then match `contentDescription` |
| 6 | **class_text** | Filter by `className` then match text |
| 7 | **xpath** | Explicit XPath expression |
| 8 | **coordinate_fallback** | Parse XML hierarchy, compute center of matching node |

### 3.3 Key Optimizations

**Fast-path before XML dump**: For regex-based `contentDescription` and `text`, the locator uses uiautomator2's native `descriptionMatches()` / `textMatches()` selectors **directly**, avoiding expensive `dump_hierarchy()` XML parsing:

```python
# Fast path (no XML dump):
el = self.device(descriptionMatches=pattern.pattern)
if el.wait(timeout=timeout):
    return el

# Fallback (XML-based):
xml = self.device.dump_hierarchy()
# ... parse XML to find matching node ...
```

**Intelligent strategy ordering**: The available criteria determine which strategies are tried — unused strategies are skipped entirely.

**Coordinate fallback**: As a last resort, the entire UI hierarchy XML is parsed to find ANY node matching the criteria. The center point of its bounds is returned as clickable coordinates. This ensures tests rarely fail on "element not found".

### 3.4 Convenience Methods

| Method | Purpose |
|---|---|
| `find(name, timeout)` | Full multi-strategy search, returns `LocatorResult` |
| `exists(name, timeout)` | Quick boolean check (`SHORT_TIMEOUT`) |
| `wait_for(name, timeout, state)` | Block until element reaches `exists` / `clickable` / `enabled` / `gone` |
| `get_text(name, timeout)` | Retrieve element text |
| `get_bounds(name, timeout)` | Retrieve element bounds as `(left, top, right, bottom)` |

### 3.5 LocatorResult

Every find operation returns a structured result:

```python
@dataclass
class LocatorResult:
    element: Optional[Any]    # uiautomator2 element object
    strategy_used: str        # Which strategy succeeded
    attempts: int             # Number of attempts made
    elapsed_ms: float         # Time taken
    found: bool               # Success flag
    info: Dict[str, Any]      # Extra debug info (coordinates, etc.)
```

---

## 4. UI Actions Module (`actions.py`)

### 4.1 UIActions — High-Level Operations

| Method | Description |
|---|---|
| `click(target, timeout, retries)` | Click element or coordinates with retry + popup dismissal |
| `long_click(target, duration)` | Long-press element or coordinates |
| `double_click(target)` | Double-click an element |
| `swipe(direction, distance)` | Swipe `up`/`down`/`left`/`right` (relative to screen size) |
| `draw_stroke(from, to, steps, duration)` | Simulate a smooth drawing stroke via multi-point swipe |
| `draw_shape(shape, center, size)` | Draw `line`/`circle`/`square`/`triangle`/`zigzag` |
| `input_text(text, target)` | Type text into a field with auto-clear |
| `launch_app()` / `stop_app()` | App lifecycle management |
| `is_app_running()` / `wait_for_app()` | App state verification |
| `press_back()` / `press_home()` | System navigation |
| `verify_text_visible(text)` | Check if text is on screen |
| `print_hierarchy_summary()` | Dump clickable elements for debugging |

### 4.2 Retry Logic

Every click operation supports:
- **Configurable retries** (`MAX_RETRIES = 3`, `RETRY_DELAY = 1.0s`)
- **Automatic popup dismissal** before each retry attempt
- **Fallback to coordinate clicking** when element found but not directly clickable

### 4.3 PopupHandler — Automatic Dialog Management

Android permission dialogs can appear unpredictably. The `PopupHandler` automatically detects and dismisses:

| Popup Type | Detection | Action |
|---|---|---|
| DrawAnywhere overlay permission | `Permission Required` / `需要权限` text | Auto-accept via `Proceed` / `继续` |
| System permission dialog | `Allow` / `允许` buttons | Auto-accept |
| Generic confirmation | `OK` / `确定` / `Yes` text | Auto-confirm |

**Fast detection**: Uses uiautomator2's native `textMatches()` / `descriptionMatches()` directly — **no XML dump needed**:

```python
def _fast_find(self, selector, timeout):
    el = self.device(descriptionMatches=desc_regex.pattern)
    if el.exists:
        return el
```

### 4.4 Drawing Simulation

Draw strokes use **multi-point swipe** to create smooth, realistic lines:

```python
def draw_stroke(self, from_pos, to_pos, steps=20, duration=0.5):
    self.device.swipe(x1, y1, x2, y2, duration, steps=steps)
```

Complex shapes (circle, square, triangle, zigzag) use programmatic point calculation with `touch.down()` → `touch.move()` → `touch.up()` sequences.

---

## 5. Base Test Framework (`base_test.py`)

### 5.1 Test Lifecycle

Every test follows a strict lifecycle managed by `BaseTest`:

```
setup()
  ├── Connect to device (uiautomator2)
  ├── Create ElementLocator
  ├── Create PopupHandler
  ├── Create UIActions
  ├── pre_test_setup()        # Subclass override (e.g., grant permissions)
  │
run_test()                    # Subclass implements (abstract)
  ├── self.step("name", action, verify, timeout, critical)
  │     ├── Execute action
  │     ├── Run optional verify() callback
  │     ├── Track timing (start → end)
  │     ├── Log result (✓ / ✗)
  │     ├── Screenshot on failure
  │     ├── Abort if critical step fails
  │     └── Return TestStepResult
  │
teardown()
  ├── post_test_cleanup()     # Subclass override
  ├── Calculate aggregate result
  └── Log summary
```

### 5.2 Step Tracking — `self.step()`

The core testing primitive. Each step:

1. **Executes** an `action` callable
2. **Verifies** state via optional `verify` callable (returns `bool`)
3. **Times** execution duration in milliseconds
4. **Screenshots** on failure (automatic)
5. **Aborts** the test if `critical=True` and the step fails

```python
self.step(
    "Launch DrawAnywhere app",
    action=lambda: self.actions.launch_app(),
    verify=lambda: self.actions.is_app_running(),
    timeout=LONG_TIMEOUT,
    critical=True,
)
```

There's also `self.optional_step()` for non-critical actions (failure won't abort the test).

### 5.3 Result Tracking

Two dataclasses capture structured results:

- **`TestStepResult`**: per-step pass/fail, duration, error, screenshot path
- **`TestCaseResult`**: aggregated test result with all steps, total duration, pass/fail

### 5.4 Common Utilities

| Method | Purpose |
|---|---|
| `ensure_app_ready()` | Launch app → handle permissions → verify toolbar visible (with retry) |
| `close_all_popups()` | Aggressively dismiss all popups (3 rounds) |
| `click_element_by_coords(selector)` | Click via bounds center — handles Compose `IconButton` nodes where the inner `Icon` is found but not clickable |

---

## 6. Test Runner (`test_runner.py`)

### 6.1 Module Registry

Tests are organized by **module** and registered in a central dictionary:

```python
TEST_REGISTRY = {
    "launch":   [TestAppLaunch, TestAppReLaunch],
    "drawing":  [TestDrawingOperations],
}

EXECUTION_ORDER = ["launch", "drawing"]  # Launch must run first
```

### 6.2 CLI Interface

```bash
python test_runner.py                              # Run all tests
python test_runner.py --modules launch drawing     # Run specific modules
python test_runner.py --verbose                    # Verbose logging
python test_runner.py --device 127.0.0.1:5555      # Specific device
python test_runner.py --clean                      # Force stop app first
python test_runner.py --list                       # List available modules
```

### 6.3 Execution Flow

1. Connect to device via uiautomator2
2. Optionally force-stop app (`--clean`)
3. Iterate modules in `EXECUTION_ORDER`
4. For each test class: instantiate → `setup()` → `run_test()` → `teardown()`
5. Collect `TestCaseResult` into `TestReport`
6. Generate HTML + JSON + console reports
7. Exit with code 0 (all passed) or 1 (any failure)

### 6.4 Crash Handling

If a test throws an unexpected exception, a synthetic `TestCaseResult` is created with status `CRASHED`, ensuring the report is always complete even if tests crash.

---

## 7. Report Generation (`report.py`)

Three output formats are generated automatically:

### 7.1 Console Summary

```
======================================================================
  DrawAnywhere GUI Automation Test Report
======================================================================
  Duration:  45.23s
  Tests:     3 total / 3 passed ✓
  Pass Rate: 100.0%
  Steps:     28 total / 28 passed
----------------------------------------------------------------------
  [✓] launch: 2/2 passed
  [✓] drawing: 1/1 passed
======================================================================
```

### 7.2 HTML Report

- Interactive, expandable test rows showing step-level details
- Color-coded pass/fail (green/red)
- Summary cards: test count, step count, duration, overall status
- Click any test row to expand and see individual step results

### 7.3 JSON Report

Structured data export with timestamps, durations, errors, and per-step details — suitable for CI/CD integration or trend analysis.

---

## 8. Test Case Modules

### 8.1 Launch Tests (`test_launch.py`)

| Test Class | Purpose | Steps |
|---|---|---|
| `TestAppLaunch` | Cold start flow | Force stop → Launch → Handle permissions → Verify toolbar → Verify core buttons (≥2/3) |
| `TestAppReLaunch` | Re-launch when running | Ensure running → Re-launch → Verify functional |

**Key design**: The `_handle_app_launch_permissions()` method handles the full overlay permission flow: detect custom dialog → accept → navigate Android Settings → grant system permission → press back.

### 8.2 Drawing Tests (`test_drawing.py`)

| Test Section | Purpose |
|---|---|
| Pen tool selection | Open tool popup → select Pen → close |
| Color picker | Open color popup → detect swatches → select color → close |
| Stroke controls | Open stroke popup → detect Width/Opacity labels → interact with sliders |
| Canvas drawing | Draw horizontal, vertical, and diagonal lines |
| Undo/Redo | Undo two strokes → expand second drawer → redo one → collapse |
| Clear canvas | Clear all strokes |
| Canvas visibility | Hide canvas → Show canvas (toggle) |
| Stroke eraser | Select eraser tool → draw over existing stroke → switch back to Pen |

**Compose-specific handling**:
- Color swatches are detected by parsing the XML hierarchy for small `clickable` elements (20-120px range)
- Slider interaction uses label-relative coordinate estimation (find "Width" text → swipe in the region below it)
- Undo/Redo buttons use `click_element_by_coords()` to avoid the Compose `IconButton` → `Icon` accessibility node issue

---

## 9. Key Design Decisions

### 9.1 Why "smart sleep" instead of fixed delays?

Fixed `time.sleep()` is fragile — too short causes flaky failures, too long wastes time. This suite uses:

- **`wait_for()` with polling**: check every 300ms with a deadline
- **Timeout per step**: each step has its own timeout based on expected operation speed
- **Retry with backoff**: retry failed clicks with popup dismissal between attempts

### 9.2 Why XML hierarchy parsing?

Compose UIs present complex challenges:
- No `resourceId` for most elements
- `contentDescription` may be on a child `Icon`, not the parent `IconButton`
- Color swatches have no text at all

The XML fallback strategy parses the full UI tree to find elements by any available attribute and compute their screen coordinates.

### 9.3 Why bilingual regex selectors?

DrawAnywhere supports both English and Chinese. Hardcoding one language would make tests locale-dependent. Regex patterns like `(Color picker|取色器)` work regardless of device language settings.

### 9.4 Why automatic popup dismissal?

Android permission dialogs appear unpredictably (first launch, after permission revoke, system updates). Manually handling them in every test is error-prone. The `PopupHandler` runs before every click operation, ensuring the test surface is always clean.

---

## 10. File Structure

```
tests/
├── config.py              # All timeouts, selectors, paths (243 lines)
├── locator.py             # Multi-strategy element finder (811 lines)
├── actions.py             # Click/swipe/draw/popup handling (836 lines)
├── base_test.py           # Test lifecycle, step tracking, utilities (499 lines)
├── report.py              # HTML/JSON/console report generation (405 lines)
├── test_runner.py         # CLI entry, orchestration (322 lines)
├── test_launch.py         # App launch + re-launch tests (257 lines)
├── test_drawing.py        # Full drawing workflow tests (539 lines)
├── requirements.txt       # Python dependencies
├── screenshots/           # Auto-captured failure screenshots
├── reports/               # Generated HTML + JSON reports
└── logs/                  # Test execution logs
```

---

## 11. Dependencies

```
uiautomator2>=2.16.0     # Android UI automation via ADB
```

The suite requires:
- **Python 3.8+**
- **Android device** with USB debugging enabled
- **uiautomator2** initialized on device: `python -m uiautomator2 init`
- **ADB** in PATH
