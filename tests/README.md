# DrawAnywhere GUI 自动化测试套件

基于 **UIAutomator2** 框架为 DrawAnywhere 安卓应用编写的高稳定性 GUI 自动化测试。

## 目录结构

```
tests/
├── config.py              # 全局配置（超时、选择器、路径）
├── locator.py             # 多策略元素定位引擎
├── actions.py             # 通用 UI 操作 + 弹窗处理
├── popup_handler.py       # (已整合到 actions.py)
├── base_test.py           # 测试基类（setup/teardown/日志/截图）
├── test_launch.py         # App 启动 & 权限处理测试
├── test_drawing.py        # 绘图操作测试（笔/颜色/粗细/橡皮擦）
├── test_toolbar.py        # 工具栏交互测试（展开/折叠/方向切换）
├── test_settings.py       # 设置页面测试
├── test_quit.py           # 退出 App 测试
├── test_runner.py         # 测试执行入口 & 报告生成
├── report.py              # 测试报告生成器（HTML/JSON/控制台）
├── requirements.txt       # Python 依赖
├── screenshots/           # 截图输出目录（自动创建）
├── reports/               # 报告输出目录（自动创建）
└── logs/                  # 日志输出目录（自动创建）
```

## 环境准备

### 1. 安装 Python 依赖

```bash
cd tests
pip install -r requirements.txt
```

### 2. 初始化 uiautomator2 到设备

```bash
# 在设备上安装 uiautomator2 agent（只需执行一次）
python -m uiautomator2 init
```

### 3. 确认设备连接

```bash
# 检查 adb 设备列表
adb devices

# 应显示类似：
# List of devices attached
# XXXXXXXX    device
```

### 4. 安装 DrawAnywhere 应用到设备

```bash
# 从项目根目录编译安装
cd ..
./gradlew installDebug

# 或直接安装 APK
adb install app/build/outputs/apk/debug/app-debug.apk
```

### 5. 授予悬浮窗权限（可选）

测试脚本会自动处理权限弹窗，但提前授予可避免弹窗干扰：

```bash
adb shell appops set com.shezik.drawanywhere SYSTEM_ALERT_WINDOW allow
```

## 运行测试

### 运行所有测试

```bash
cd tests
python test_runner.py
```

### 运行指定模块

```bash
# 只运行启动测试
python test_runner.py --modules launch

# 运行启动 + 绘图测试
python test_runner.py --modules launch drawing

# 运行设置 + 退出测试
python test_runner.py --modules settings quit
```

### 可用模块

| 模块名 | 测试内容 |
|--------|----------|
| `launch` | App 启动流程、权限弹窗处理、重新启动 |
| `drawing` | 画笔/橡皮擦选择、颜色选择器、粗细/透明度调节、画布绘制、撤销/重做、清空画布 |
| `toolbar` | 工具栏展开/折叠、触摸透传切换、方向切换（横向/竖向） |
| `settings` | 设置页面、自动清空画布选项、启动显示选项、关于页 |
| `quit` | 退出应用、服务停止验证、重新启动验证 |

### 其他参数

```bash
# 显示所有参数
python test_runner.py --help

# 详细日志输出
python test_runner.py --verbose

# 指定设备（多设备时）
python test_runner.py --device 127.0.0.1:5555
python test_runner.py --device emulator-5554

# 强制停止 App 后开始测试（清理环境）
python test_runner.py --clean

# 列出所有测试模块
python test_runner.py --list
```

## 测试报告

运行后自动生成三种格式的报告：

| 格式 | 位置 | 说明 |
|------|------|------|
| **控制台** | 标准输出 | 实时显示，包含通过/失败汇总 |
| **HTML** | `reports/test_report_*.html` | 可视化报告，可展开查看每步详情 |
| **JSON** | `reports/test_results_*.json` | 结构化数据，便于 CI/CD 集成 |

截图存放在 `screenshots/` 目录，失败步骤会自动截图。

## 核心设计

### 1. 多策略元素定位 (`locator.py`)

由于 Jetpack Compose 不暴露传统 Android View ID，定位采用多级回退策略：

```
策略优先级:
  1. content-desc 精确匹配     ← Compose contentDescription
  2. content-desc 模糊匹配     ← 正则/包含
  3. text 精确匹配            ← Compose Text 组件
  4. text 正则匹配            ← 多语言文本匹配
  5. className + desc 组合    ← 层级定位
  6. className + text 组合    
  7. XPath                   ← 绝对定位
  8. 坐标推算（兜底方案）      ← 解析 XML 树估算位置
```

**关键特性**：
- 所有选择器支持中/英文正则匹配（如 `r"(Undo|撤销)"`）
- 定位失败自动截图 + dump UI 控件树
- 坐标推算使用点击元素边界中心，适配不同分辨率

### 2. 智能等待机制 (`actions.py`)

- **`wait_for(state)`**：等待元素达到指定状态（exists / clickable / enabled / gone）
- **可配置超时**：`config.py` 中设置 `DEFAULT_TIMEOUT=15s`、`LONG_TIMEOUT=30s`
- **Compose 动画适配**：`ANIMATION_WAIT=1.5s` 等待动画完成后操作
- **轮询间隔**：300ms 轮询，避免空转

### 3. 弹窗干扰处理 (`actions.py` 中 `PopupHandler`)

自动检测并处理：
- DrawAnywhere 悬浮窗权限对话框
- Android 系统权限请求弹窗
- 通用确认/取消对话框
  
处理方式：
- 自动点击 "允许/继续/Proceed" 按钮
- 支持按 Back 键关闭弹窗
- 每次操作前自动检查并关闭弹窗

### 4. 异常处理 & 重试

- **操作级重试**：关键点击/定位操作支持 2-3 次重试（`MAX_RETRIES=3`）
- **异常时截图**：`ElementNotFoundError` / `TimeoutError` 自动截图保存
- **控件树输出**：定位失败时 dump 完整 UI hierarchy 到日志
- **测试隔离**：单个步骤失败不阻塞后续步骤（非关键步骤标记 `critical=False`）

### 5. 设备适配

- **分辨率无关**：所有坐标使用屏幕百分比或元素边界计算
- **Android 8.0+ 兼容**：不使用 API level 特定功能
- **语言无关**：所有选择器使用正则同时匹配中/英文
- **无绝对坐标**：优先使用元素定位，兜底方案基于 XML 树推算

## 关于保存/分享功能

当前版本的 DrawAnywhere 是一个悬浮绘图工具，暂未内置保存/分享功能。测试套件已适配：
- 设置持久化验证（通过 UI 交互确认状态保存）
- 预留了文件系统验证接口（`verify_element_exists` 可扩展为文件校验）

如需测试保存/分享功能，请在 DrawAnywhere 中实现后扩展以下方法：
```python
# 扩展 test_drawing.py 的 TestDrawingOperations 类
def _test_save_drawing(self):
    """保存绘图到文件"""
    self.step("Click save button", lambda: self.actions.click("save_btn"))
    self.step("Verify file exists", 
              verify=lambda: self._check_saved_file_exists())

def _check_saved_file_exists(self) -> bool:
    """检查保存的文件是否存在"""
    output = self.device.shell(
        "ls /sdcard/Pictures/DrawAnywhere/*.png 2>/dev/null"
    )
    return bool(output.output.strip())
```

## 定位失败排查思路

当元素定位失败时，按以下步骤排查：

### Step 1: 查看截图
```
tests/screenshots/FAIL_*.png
```
确认目标元素是否实际出现在屏幕上。

### Step 2: 查看控件树
失败时自动输出到日志，也可手动导出：
```python
# 在测试中添加
self.actions.print_hierarchy_summary()
```

关键查找字段：
- `content-desc`：Compose 的 contentDescription
- `text`：Compose 的 Text 内容
- `class`：Android 控件类名（Compose 多为 `android.widget.ImageButton` 或 `android.view.View`）

### Step 3: 检查多语言匹配
确认 `config.py` 中 `SELECTORS` 的 `desc_regex` / `text_regex` 涵盖了当前系统语言。

### Step 4: 增加 timeout
如果控件加载慢（老旧设备），增大 `config.py` 中的 `DEFAULT_TIMEOUT`。

### Step 5: 使用坐标兜底
如果控件确实无法通过属性定位（如纯图形色块），坐标推算会自动生效。调大 `ANIMATION_WAIT` 确保动画完毕。

## CI/CD 集成示例

### GitHub Actions

```yaml
- name: Run GUI Tests
  run: |
    cd tests
    pip install -r requirements.txt
    python -m uiautomator2 init
    python test_runner.py --clean

- name: Upload Reports
  uses: actions/upload-artifact@v3
  if: always()
  with:
    name: test-reports
    path: tests/reports/
```

## License

本项目测试代码遵循 AGPLv3 协议，与 DrawAnywhere 项目保持一致。
