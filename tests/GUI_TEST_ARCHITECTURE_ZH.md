# DrawAnywhere GUI 自动化测试 — 架构与设计文档

> **框架**: Python + UIAutomator2  
> **测试目标**: Jetpack Compose Android 应用（无传统 resource ID）  
> **测试模块**: `launch`（启动）/ `drawing`（绘图）  
> **最后更新**: 2026-06-16

---

## 1. 整体架构

测试套件采用分层架构，各层职责清晰：

```
┌──────────────────────────────────────────────────────┐
│                   test_runner.py                      │  ← 命令行入口，测试编排
├──────────────────────────────────────────────────────┤
│  test_launch.py          test_drawing.py              │  ← 测试用例模块
├──────────────────────────────────────────────────────┤
│                    base_test.py                        │  ← 公共生命周期、步骤追踪
├────────────────────────┬─────────────────────────────┤
│     actions.py          │       locator.py             │  ← 核心引擎
│  （点击/滑动/绘图/      │  （多策略元素定位，         │
│    弹窗处理）           │    专为 Compose 设计）       │
├────────────────────────┴─────────────────────────────┤
│                    config.py                           │  ← 所有超时、选择器、路径配置
├──────────────────────────────────────────────────────┤
│                    report.py                           │  ← HTML / JSON / 控制台报告
└──────────────────────────────────────────────────────┘
```

所有测试模块均继承自 `BaseTest`，它提供自动设备连接、日志记录、失败截图和逐步骤结果追踪。

---

## 2. 配置系统（`config.py`）

所有参数集中在一个文件中管理——测试代码中不存在任何硬编码的魔法数字。

### 2.1 分层超时策略

为了在可靠性和速度之间取得平衡，超时时间被分为多个层级：

| 常量 | 默认值 | 用途 |
|---|---|---|
| `DEFAULT_TIMEOUT` | **15 秒** | 标准元素等待时间 |
| `SHORT_TIMEOUT` | **5 秒** | 快速操作（按钮点击响应、存在性检查） |
| `LONG_TIMEOUT` | **30 秒** | 应用启动、复杂动画、权限流程 |
| `POPUP_TIMEOUT` | **1 秒** | 弹窗快速检测（使用原生选择器，无需 XML dump） |
| `IDLE_TIMEOUT` | **2 秒** | 操作后等待 UI 稳定 |
| `ANIMATION_WAIT` | **1.5 秒** | 等待 Compose 动画完成 |
| `RETRY_DELAY` | **1.0 秒** | 重试间隔 |
| `MAX_RETRIES` | **3 次** | 关键操作最大重试次数 |

**设计考量**：分层超时避免了常见的"flaky test"问题：
- **短超时**用于应该快速出现的元素（按钮响应等）
- **长超时**用于应用级操作（冷启动、权限授权流程）
- **自适应重试**：带退避策略的重试，而非立即失败

### 2.2 绘图模拟参数

```
DRAW_STROKE_STEPS    = 20          # 中间触摸点数（保证笔画平滑）
DRAW_STROKE_DURATION = 0.5 秒     # 单笔总时长（模拟人类绘制速度）
```

### 2.3 双语选择器

每个 UI 元素都使用**基于正则的双语匹配模式**（同时支持中英文）：

```python
"visibility": {
    "desc_regex": re.compile(
        r"(Hide canvas|Show canvas|隐藏画布|显示画布)", re.IGNORECASE
    ),
}
```

这确保了同一套测试代码无需修改即可在英文和中文设备上运行。

### 2.4 截图与报告配置

- `SCREENSHOT_ON_FAILURE = True` — 每个失败步骤自动截图
- `SCREENSHOT_ON_STEP = False` — 可选的每步骤截图（调试模式）
- 所有截图存放在 `tests/screenshots/`
- 报告存放在 `tests/reports/`（HTML + JSON 两种格式）

---

## 3. 多策略元素定位器（`locator.py`）

> **这是整个测试套件的核心创新点。**

### 3.1 问题背景

Jetpack Compose 界面**没有**传统的 Android 资源 ID（`android:id/...`）。元素的识别依赖于：

- `contentDescription`（无障碍描述标签）
- `text`（可见文本）
- `className`（类名，如 `android.widget.ImageButton`）
- 布局边界（像素坐标）

传统的 `findElementById()` 对 Compose UI **完全无效**。

### 3.2 解决方案：8 级策略回退链

`ElementLocator.find()` 按顺序尝试以下策略，在首次成功时停止：

| # | 策略 | 说明 |
|---|---|---|
| 1 | **description**（精确匹配） | 完全匹配 `contentDescription` |
| 2 | **description_contains** | 子串 / 正则匹配 `contentDescription` |
| 3 | **text**（精确匹配） | 完全匹配可见文本 |
| 4 | **text_contains** | 子串 / 正则匹配文本 |
| 5 | **class_desc** | 按 `className` 筛选后再匹配 `contentDescription` |
| 6 | **class_text** | 按 `className` 筛选后再匹配文本 |
| 7 | **xpath** | 显式 XPath 表达式 |
| 8 | **coordinate_fallback** | 解析 XML 层级，计算匹配节点的中心坐标 |

### 3.3 关键性能优化

**快速通道（Fast Path）——XML dump 前的原生查询**：对于基于正则的 `contentDescription` 和 `text`，定位器直接使用 uiautomator2 的原生 `descriptionMatches()` / `textMatches()` 选择器，避免昂贵的 `dump_hierarchy()` XML 解析：

```python
# 快速通道（无需 XML dump）：
el = self.device(descriptionMatches=pattern.pattern)
if el.wait(timeout=timeout):
    return el

# 回退方案（XML 解析）：
xml = self.device.dump_hierarchy()
# ... 解析 XML 查找匹配节点 ...
```

**智能策略排序**：根据可用的匹配条件决定尝试哪些策略，不相关策略直接跳过。

**坐标回退（Coordinate Fallback）**：作为最后的兜底手段，解析整个 UI 层级 XML，查找**任何**匹配条件的节点，将其边界中心点作为可点击坐标返回。这确保了测试极少因"找不到元素"而失败。

### 3.4 便捷方法

| 方法 | 用途 |
|---|---|
| `find(name, timeout)` | 完整多策略搜索，返回 `LocatorResult` |
| `exists(name, timeout)` | 快速布尔检查（使用 `SHORT_TIMEOUT`） |
| `wait_for(name, timeout, state)` | 阻塞等待元素达到 `exists` / `clickable` / `enabled` / `gone` 状态 |
| `get_text(name, timeout)` | 获取元素文本 |
| `get_bounds(name, timeout)` | 获取元素边界 `(left, top, right, bottom)` |

### 3.5 LocatorResult 结构

每次查找操作都返回结构化结果：

```python
@dataclass
class LocatorResult:
    element: Optional[Any]    # uiautomator2 元素对象
    strategy_used: str        # 成功时使用的策略名称
    attempts: int             # 尝试次数
    elapsed_ms: float         # 耗时（毫秒）
    found: bool               # 是否找到
    info: Dict[str, Any]      # 额外调试信息（坐标等）
```

---

## 4. UI 操作模块（`actions.py`）

### 4.1 UIActions — 高级 UI 操作

| 方法 | 说明 |
|---|---|
| `click(target, timeout, retries)` | 点击元素或坐标，支持重试和自动弹窗关闭 |
| `long_click(target, duration)` | 长按元素或坐标 |
| `double_click(target)` | 双击元素 |
| `swipe(direction, distance)` | 向 `up`/`down`/`left`/`right` 滑动（相对屏幕尺寸） |
| `draw_stroke(from, to, steps, duration)` | 通过多点滑动模拟平滑绘制笔画 |
| `draw_shape(shape, center, size)` | 绘制 `line`/`circle`/`square`/`triangle`/`zigzag` |
| `input_text(text, target)` | 向输入框输入文本（支持自动清空） |
| `launch_app()` / `stop_app()` | 应用生命周期管理 |
| `is_app_running()` / `wait_for_app()` | 应用状态验证 |
| `press_back()` / `press_home()` | 系统导航 |
| `verify_text_visible(text)` | 检查屏幕上是否显示指定文本 |
| `print_hierarchy_summary()` | 打印可点击元素摘要（调试用） |

### 4.2 重试机制

每次点击操作都支持：
- **可配置重试**（`MAX_RETRIES = 3`，`RETRY_DELAY = 1.0s`）
- **每次重试前自动关闭弹窗**
- **回退坐标点击**：当元素被找到但不可直接点击时，回退到坐标点击

### 4.3 PopupHandler — 自动弹窗管理

Android 权限对话框可能不可预测地出现。`PopupHandler` 自动检测并关闭：

| 弹窗类型 | 检测方式 | 处理动作 |
|---|---|---|
| DrawAnywhere 悬浮窗权限 | `Permission Required` / `需要权限` 文本 | 自动通过 `Proceed` / `继续` |
| 系统权限对话框 | `Allow` / `允许` 按钮 | 自动允许 |
| 通用确认对话框 | `OK` / `确定` / `Yes` 文本 | 自动确认 |

**快速检测**：直接使用 uiautomator2 的原生 `textMatches()` / `descriptionMatches()` ——**无需 XML dump**：

```python
def _fast_find(self, selector, timeout):
    el = self.device(descriptionMatches=desc_regex.pattern)
    if el.exists:
        return el
```

### 4.4 绘图模拟实现

绘制笔画使用**多点滑动**来创建平滑、逼真的线条：

```python
def draw_stroke(self, from_pos, to_pos, steps=20, duration=0.5):
    self.device.swipe(x1, y1, x2, y2, duration, steps=steps)
```

复杂图形（圆、正方形、三角形、锯齿线）使用编程计算点位 + `touch.down()` → `touch.move()` → `touch.up()` 序列。

---

## 5. 基础测试框架（`base_test.py`）

### 5.1 测试生命周期

每个测试都遵循由 `BaseTest` 管理的严格生命周期：

```
setup()
  ├── 连接设备（uiautomator2）
  ├── 创建 ElementLocator
  ├── 创建 PopupHandler
  ├── 创建 UIActions
  ├── pre_test_setup()        # 子类可覆写（例如：授权权限）
  │
run_test()                    # 子类实现（抽象方法）
  ├── self.step("名称", action, verify, timeout, critical)
  │     ├── 执行 action
  │     ├── 运行可选的 verify() 回调
  │     ├── 记录耗时（开始 → 结束）
  │     ├── 记录结果（✓ / ✗）
  │     ├── 失败时自动截图
  │     ├── 关键步骤失败时中止测试
  │     └── 返回 TestStepResult
  │
teardown()
  ├── post_test_cleanup()     # 子类可覆写
  ├── 计算汇总结果
  └── 记录摘要
```

### 5.2 步骤追踪 — `self.step()`

这是整个测试框架的核心原语。每个步骤：

1. **执行** `action` 可调用对象
2. **验证**状态（通过可选的 `verify` 回调，返回 `bool`）
3. **计时**执行时长（毫秒级）
4. **截图**（失败时自动触发）
5. **中止**测试（如果 `critical=True` 且步骤失败）

```python
self.step(
    "启动 DrawAnywhere 应用",
    action=lambda: self.actions.launch_app(),
    verify=lambda: self.actions.is_app_running(),
    timeout=LONG_TIMEOUT,
    critical=True,
)
```

此外还有 `self.optional_step()` 用于非关键操作（失败不会中止测试）。

### 5.3 结果数据结构

两个 dataclass 捕获结构化结果：

- **`TestStepResult`**：每步的通过/失败、耗时、错误信息、截图路径
- **`TestCaseResult`**：汇总的测试结果，包含所有步骤、总耗时、通过/失败状态

### 5.4 公共工具方法

| 方法 | 用途 |
|---|---|
| `ensure_app_ready()` | 启动应用 → 处理权限 → 验证工具栏可见（含重试） |
| `close_all_popups()` | 激进关闭所有弹窗（3 轮） |
| `click_element_by_coords(selector)` | 通过边界中心点击 — 处理 Compose `IconButton` 节点问题（找到的是内部 `Icon` 节点但不可点击） |

---

## 6. 测试运行器（`test_runner.py`）

### 6.1 模块注册表

测试按**模块**组织，注册在中央字典中：

```python
TEST_REGISTRY = {
    "launch":   [TestAppLaunch, TestAppReLaunch],
    "drawing":  [TestDrawingOperations],
}

EXECUTION_ORDER = ["launch", "drawing"]  # 启动测试必须先运行
```

### 6.2 命令行接口

```bash
python test_runner.py                              # 运行全部测试
python test_runner.py --modules launch drawing     # 运行指定模块
python test_runner.py --verbose                    # 详细日志输出
python test_runner.py --device 127.0.0.1:5555      # 指定设备
python test_runner.py --clean                      # 先强制停止应用
python test_runner.py --list                       # 列出可用模块
```

### 6.3 执行流程

1. 通过 uiautomator2 连接设备
2. 可选强制停止应用（`--clean`）
3. 按 `EXECUTION_ORDER` 顺序遍历模块
4. 对每个测试类：实例化 → `setup()` → `run_test()` → `teardown()`
5. 收集 `TestCaseResult` 到 `TestReport`
6. 生成 HTML + JSON + 控制台报告
7. 退出码 0（全部通过）或 1（存在失败）

### 6.4 崩溃处理

如果测试抛出意外异常，会创建一个状态为 `CRASHED` 的合成 `TestCaseResult`，确保报告始终完整，即使测试崩溃也不会丢失记录。

---

## 7. 报告生成（`report.py`）

自动生成三种输出格式：

### 7.1 控制台摘要

```
======================================================================
  DrawAnywhere GUI Automation Test Report
======================================================================
  耗时:      45.23 秒
  测试用例:  3 总计 / 3 通过 ✓
  通过率:    100.0%
  步骤:      28 总计 / 28 通过
----------------------------------------------------------------------
  [✓] launch: 2/2 通过
  [✓] drawing: 1/1 通过
======================================================================
```

### 7.2 HTML 报告

- 可交互、可展开的测试行，显示步骤级详情
- 颜色编码的通过/失败（绿色/红色）
- 摘要卡片：测试数量、步骤数量、耗时、总体状态
- 点击任意测试行可展开查看单步结果

### 7.3 JSON 报告

结构化数据导出，包含时间戳、耗时、错误信息和逐步骤详情——适合 CI/CD 集成或趋势分析。

---

## 8. 测试用例模块

### 8.1 启动测试（`test_launch.py`）

| 测试类 | 目的 | 步骤 |
|---|---|---|
| `TestAppLaunch` | 冷启动流程 | 强制停止 → 启动 → 处理权限 → 验证工具栏 → 验证核心按钮（至少 2/3） |
| `TestAppReLaunch` | 已运行时重新启动 | 确保运行中 → 重新启动 → 验证功能正常 |

**关键设计**：`_handle_app_launch_permissions()` 方法处理完整的悬浮窗权限流程：检测自定义对话框 → 接受 → 导航到 Android 设置 → 授予系统权限 → 按返回键。

### 8.2 绘图测试（`test_drawing.py`）

| 测试部分 | 目的 |
|---|---|
| 笔工具选择 | 打开工具弹窗 → 选择钢笔 → 关闭 |
| 颜色选择器 | 打开颜色弹窗 → 检测色块 → 选择颜色 → 关闭 |
| 笔画控制 | 打开笔画弹窗 → 检测宽度/不透明度标签 → 与滑块交互 |
| 画布绘制 | 绘制水平线、垂直线和对角线 |
| 撤销/重做 | 撤销两笔 → 展开第二抽屉 → 重做一笔 → 收起 |
| 清空画布 | 清除所有笔画 |
| 画布可见性 | 隐藏画布 → 显示画布（切换） |
| 笔画橡皮擦 | 选择橡皮擦工具 → 在已有笔画上滑动擦除 → 切回钢笔 |

**Compose 特殊处理**：
- 颜色色块通过解析 XML 层级中**小尺寸可点击元素**（20-120px 范围）来检测
- 滑块交互使用标签相对坐标估算（找到 "Width" 文本 → 在其下方区域滑动）
- 撤销/重做按钮使用 `click_element_by_coords()` 避免 Compose `IconButton` → `Icon` 无障碍节点问题

---

## 9. 关键设计决策

### 9.1 为什么用"智能等待"而非固定延时？

固定的 `time.sleep()` 很脆弱——太短导致不稳定失败，太长浪费时间。本套件使用：

- **带轮询的 `wait_for()`**：每 300ms 检查一次，有截止时间
- **每步独立超时**：每个步骤根据预期操作速度设置各自的超时
- **带退避的重试**：失败后重试，每次重试前关闭弹窗

### 9.2 为什么需要 XML 层级解析？

Compose UI 带来复杂的挑战：
- 大多数元素没有 `resourceId`
- `contentDescription` 可能在子 `Icon` 上，而非父 `IconButton` 上
- 颜色色块完全没有文本

XML 回退策略解析整个 UI 树，通过任何可用属性查找元素并计算其屏幕坐标。

### 9.3 为什么使用双语正则选择器？

DrawAnywhere 同时支持英文和中文。硬编码单一语言会使测试依赖设备语言设置。正则模式如 `(Color picker|取色器)` 无论设备语言设置如何都能工作。

### 9.4 为什么自动处理弹窗？

Android 权限对话框不可预测地出现（首次启动、权限被撤销后、系统更新等）。在每个测试中手动处理它们容易出错。`PopupHandler` 在每次点击操作前运行，确保测试界面始终干净。

---

## 10. 文件结构

```
tests/
├── config.py              # 所有超时、选择器、路径配置（243 行）
├── locator.py             # 多策略元素定位器（811 行）
├── actions.py             # 点击/滑动/绘图/弹窗处理（836 行）
├── base_test.py           # 测试生命周期、步骤追踪、工具方法（499 行）
├── report.py              # HTML/JSON/控制台报告生成（405 行）
├── test_runner.py         # 命令行入口、测试编排（322 行）
├── test_launch.py         # 应用启动 + 重新启动测试（257 行）
├── test_drawing.py        # 完整绘图流程测试（539 行）
├── requirements.txt       # Python 依赖
├── screenshots/           # 自动捕获的失败截图
├── reports/               # 生成的 HTML + JSON 报告
└── logs/                  # 测试执行日志
```

---

## 11. 依赖

```
uiautomator2>=2.16.0     # 通过 ADB 进行 Android UI 自动化
```

运行要求：
- **Python 3.8+**
- **Android 设备**已开启 USB 调试
- 设备上已初始化 **uiautomator2**：`python -m uiautomator2 init`
- **ADB** 在 PATH 中
