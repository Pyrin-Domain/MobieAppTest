# DrawAnywhere 单元测试文档

## 概述

本文档提供了 DrawAnywhere Android 应用程序的单元测试设置、测试覆盖率和测试策略的详细信息。

## 测试框架设置

### 添加的依赖项

#### 1. **MockK** (版本 1.13.8)
- **用途**: Kotlin 原生模拟库，用于创建模拟对象
- **使用场景**: 在 ViewModel 测试中模拟依赖项
- **位置**: `gradle/libs.versions.toml` 和 `app/build.gradle.kts`

#### 2. **Robolectric** (版本 4.11.1)
- **用途**: Android 测试框架，在 JVM 上运行测试
- **使用场景**: 测试 Android 特定组件，无需模拟器
- **位置**: `gradle/libs.versions.toml` 和 `app/build.gradle.kts`

#### 3. **JaCoCo** (内置 Gradle 插件)
- **用途**: 代码覆盖率测量工具
- **使用场景**: 生成单元测试的代码覆盖率报告
- **配置**: 在 `app/build.gradle.kts` 中启用 `jacoco` 插件

### 构建配置更改

```kotlin
// app/build.gradle.kts
plugins {
    jacoco  // 添加 JaCoCo 插件
}

android {
    testOptions {
        unitTests {
            isIncludeAndroidResources = true  // 在单元测试中启用 Android 资源
        }
    }
    
    buildTypes {
        debug {
            enableUnitTestCoverage = true      // 启用单元测试覆盖率
            enableAndroidTestCoverage = true   // 启用 Android 测试覆盖率
        }
    }
}
```

## 创建的测试文件

### 1. **DrawControllerTest.kt** (基于 MockK)
**位置**: `app/src/test/java/com/shezik/drawanywhere/DrawControllerTest.kt`

**测试覆盖**:
- 路径创建和操作
- 撤销/重做功能
- 笔划橡皮擦行为
- 路径清除操作
- 边界情况（空路径、撤销深度限制）
- 状态管理（canUndo, canRedo, canClearPaths）

**测试数量**: 15 个测试用例

**关键测试场景**:
```kotlin
- testCreatePath_addsPathToList()           // 创建路径并添加到列表
- testUpdateLatestPath_addsPointToExistingPath()  // 更新最新路径
- testFinishPath_addsToUndoStack()          // 完成路径并添加到撤销栈
- testUndo_removesLastPath()                // 撤销移除最后一条路径
- testRedo_restoresUndonePath()             // 重做恢复已撤销的路径
- testClearPaths_removesAllPaths()          // 清除所有路径
- testStrokeEraser_removesPathOnTouch()     // 笔划橡皮擦触摸时移除路径
- testMultipleUndoOperations()              // 多次撤销操作
- testUndoDepthLimit()                      // 撤销深度限制
- testNewActionClearsRedoStack()            // 新操作清除重做栈
```

### 2. **DrawUtilsTest.kt** (纯 JUnit)
**位置**: `app/src/test/java/com/shezik/drawanywhere/DrawUtilsTest.kt`

**测试覆盖**:
- 距离计算（distance, distanceSquared）
- 点到线段的距离
- 中点计算
- 从点生成路径

**测试数量**: 14 个测试用例

**关键测试场景**:
```kotlin
- testDistanceSquared_samePoint_returnsZero()           // 同一点的距离平方为零
- testDistanceSquared_differentPoints_calculatesCorrectly()  // 不同点的距离平方
- testDistancePointToLineSegment_pointOnLine_returnsZero()   // 线上的点距离为零
- testCalculateMidpoint_calculatesCorrectly()           // 中点计算正确
- testPointsToPath_emptyList_returnsEmptyPath()         // 空列表返回空路径
- testPointsToPath_multiplePoints_createsSmoothPath()   // 多点创建平滑路径
```

### 3. **DrawViewModelTest.kt** (基于 MockK)
**位置**: `app/src/test/java/com/shezik/drawanywhere/DrawViewModelTest.kt`

**测试覆盖**:
- UI 状态管理
- 笔配置更改（颜色、宽度、透明度）
- 画布可见性和穿透切换
- 工具栏定位和方向
- 抽屉状态管理
- 按钮固定功能
- 自动清除画布功能
- 笔划处理（开始、更新、完成）

**测试数量**: 35+ 个测试用例

**关键测试场景**:
```kotlin
- testInitialState_valuesAreCorrect()           // 初始状态值正确
- testSwitchToPen_changesPenType()              // 切换笔类型
- testSetPenColor_updatesPenConfig()            // 设置笔颜色
- testToggleCanvasVisibility_togglesVisibility() // 切换画布可见性
- testToggleCanvasPassthrough_togglesPassthrough() // 切换画布穿透
- testClearCanvas_callsController()             // 清除画布调用控制器
- testSetToolbarPosition_updatesServiceState()  // 设置工具栏位置
- testPinSecondDrawerButton_pinsButton()        // 固定第二个抽屉按钮
- testQuitApplication_stopsService()            // 退出应用停止服务
- testAutoClearCanvas_clearsOnHide()            // 隐藏时自动清除画布
```

**模拟策略**:
```kotlin
private lateinit var mockController: DrawController
private lateinit var mockPreferencesMgr: PreferencesManager

@Before
fun setup() {
    mockController = mockk(relaxed = true)
    mockPreferencesMgr = mockk(relaxed = true)
    
    viewModel = DrawViewModel(
        controller = mockController,
        preferencesMgr = mockPreferencesMgr,
        initialUiState = UiState(),
        initialServiceState = ServiceState(),
        stopService = { serviceStopped = true }
    )
}
```

### 4. **DataClassTest.kt** (纯 JUnit)
**位置**: `app/src/test/java/com/shezik/drawanywhere/DataClassTest.kt`

**测试覆盖**:
- PenConfig 数据类
- PathWrapper 数据类
- ServiceState 数据类
- UiState 数据类
- DrawAction 密封类
- 枚举类型（PenType, ToolbarOrientation, StrokeModifier）

**测试数量**: 20+ 个测试用例

**关键测试场景**:
```kotlin
- testPenConfig_defaultValues()                 // 默认值测试
- testPenConfig_copy_createsNewInstance()       // copy 创建新实例
- testPathWrapper_creation()                    // PathWrapper 创建
- testPathWrapper_cachedPath_generation()       // 缓存路径生成
- testServiceState_defaultValues()              // ServiceState 默认值
- testUiState_currentPenConfig_returnsCorrectConfig() // 当前笔配置
- testDefaultPenConfigs_returnsExpectedMap()    // 默认笔配置映射
```

### 5. **PreferencesManagerRobolectricTest.kt** (基于 Robolectric)
**位置**: `app/src/test/java/com/shezik/drawanywhere/PreferencesManagerRobolectricTest.kt`

**测试覆盖**:
- 保存和检索 UI 状态
- 笔配置持久化
- 服务状态持久化
- 枚举值解析
- DataStore 集成
- 偏好设置覆盖

**测试数量**: 12 个测试用例

**关键测试场景**:
```kotlin
- testGetSavedUiState_returnsDefaultWhenNoPreferences()  // 无偏好时返回默认值
- testSaveAndRetrieveUiState()                           // 保存和检索 UI 状态
- testSaveAndRetrievePenConfigs()                        // 保存和检索笔配置
- testGetEnumValueOrDefault_returnsDefaultWhenInvalid()  // 无效值返回默认值
- testSaveMultipleTimes_overwritesPreviousValues()       // 多次保存覆盖之前的值
```

**Robolectric 配置**:
```kotlin
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])  // Android API 级别 33
class PreferencesManagerRobolectricTest {
    private lateinit var context: Context
    
    @Before
    fun setup() {
        context = RuntimeEnvironment.getApplication()
        preferencesManager = PreferencesManager(context)
    }
}
```

### 6. **DrawControllerRobolectricTest.kt** (基于 Robolectric)
**位置**: `app/src/test/java/com/shezik/drawanywhere/DrawControllerRobolectricTest.kt`

**测试覆盖**:
- 可观察路径列表行为
- Flow 状态发射
- 复杂绘图序列
- 笔划橡皮擦检测精度
- 带擦除操作的撤销/重做
- 路径缓存机制
- 并发路径操作

**测试数量**: 15+ 个测试用例

**关键测试场景**:
```kotlin
- testFlowStates_emitCorrectValues()              // Flow 状态发射正确值
- testComplexDrawingSequence()                    // 复杂绘图序列
- testErasePathWithStrokeEraser_detectsAndRemovesPath() // 橡皮擦检测并移除路径
- testUndoRedoWithEraseActions()                  // 带擦除操作的撤销重做
- testPathWrapper_caching_worksCorrectly()        // PathWrapper 缓存工作正常
- testUndoStackDepthLimit_preventsOverflow()      // 撤销栈深度限制防止溢出
```

## 运行测试

### 运行所有单元测试
```bash
./gradlew test
```

### 运行带覆盖率的测试
```bash
./gradlew testDebugUnitTestCoverage
```

### 运行特定测试类
```bash
./gradlew test --tests "com.shezik.drawanywhere.DrawControllerTest"
```

### 仅运行 Robolectric 测试
```bash
./gradlew testDebugUnitTest --tests "*RobolectricTest"
```

## 代码覆盖率报告

### 生成覆盖率报告

运行启用覆盖率的测试后，报告生成在：

```
app/build/reports/jacoco/testDebugUnitTestCoverage/html/index.html
```

### 查看覆盖率报告

1. 运行带覆盖率的测试：
   ```bash
   ./gradlew clean testDebugUnitTestCoverage
   ```

2. 在浏览器中打开 HTML 报告：
   ```
   app/build/reports/jacoco/testDebugUnitTestCoverage/html/index.html
   ```

3. 报告显示：
   - 行覆盖率
   - 分支覆盖率
   - 方法覆盖率
   - 类覆盖率

### 预期覆盖率指标

基于创建的测试套件：

| 组件 | 预期覆盖率 | 测试类型 |
|------|-----------|---------|
| DrawController | 85-95% | MockK + Robolectric |
| DrawViewModel | 80-90% | MockK |
| DrawUtils | 95-100% | 纯 JUnit |
| 数据类 | 90-100% | 纯 JUnit |
| PreferencesManager | 75-85% | Robolectric |
| **总计** | **80-90%** | **混合** |

## 测试架构

### 测试层次

1. **单元测试（纯 JUnit）**
   - 测试纯函数和数据类
   - 无 Android 依赖
   - 执行最快
   - 示例：`DrawUtilsTest`, `DataClassTest`

2. **模拟测试（MockK）**
   - 使用模拟依赖测试业务逻辑
   - 隔离 ViewModel 逻辑
   - 验证交互
   - 示例：`DrawViewModelTest`, `DrawControllerTest`

3. **Android 测试（Robolectric）**
   - 测试 Android 特定组件
   - JVM 上的真实 Android 框架
   - 测试 DataStore 集成
   - 示例：`PreferencesManagerRobolectricTest`

### 测试组织

```
app/src/test/java/com/shezik/drawanywhere/
├── DrawControllerTest.kt              # MockK 测试
├── DrawControllerRobolectricTest.kt   # Robolectric 测试
├── DrawViewModelTest.kt               # MockK 测试
├── DrawUtilsTest.kt                   # 纯 JUnit 测试
├── DataClassTest.kt                   # 纯 JUnit 测试
├── PreferencesManagerRobolectricTest.kt # Robolectric 测试
└── ExampleUnitTest.kt                 # 原始示例测试
```

## 实施的测试最佳实践

### 1. **Given-When-Then 模式**
```kotlin
@Test
fun testExample() = runBlocking {
    // Given (给定)
    val input = createTestData()
    
    // When (当)
    val result = systemUnderTest.process(input)
    
    // Then (那么)
    assertEquals(expected, result)
}
```

### 2. **描述性测试名称**
- 格式：`test[方法]_[场景]_[预期结果]`
- 示例：`testClearCanvas_callsController()`

### 3. **隔离测试**
- 每个测试独立
- 每次测试全新设置
- 无共享可变状态

### 4. **边界情况测试**
- 空集合
- 空值
- 边界条件
- 错误状态

### 5. **协程测试**
```kotlin
@OptIn(ExperimentalCoroutinesApi::class)
private val testDispatcher = StandardTestDispatcher()

@Before
fun setup() {
    Dispatchers.setMain(testDispatcher)
}

@Test
fun testCoroutineFunction() = runBlocking {
    // 测试代码
    testDispatcher.scheduler.advanceUntilIdle()
}
```

## 覆盖率改进策略

### 当前覆盖率缺口

1. **UI 组件（Compose）**
   - DrawCanvas 可组合函数
   - DrawToolbar 可组合函数
   - MainActivity
   
   **建议**: 使用 `createComposeRule()` 添加 Compose UI 测试

2. **服务组件**
   - MainService
   - DrawAnywhereTileService
   
   **建议**: 添加 Robolectric 服务测试

3. **集成场景**
   - 完整绘图工作流程
   - 应用重启后的设置持久化
   
   **建议**: 添加集成测试

### 未来测试添加

1. **Compose UI 测试**
```kotlin
@get:Rule
val composeTestRule = createComposeRule()

@Test
fun testDrawToolbar_rendersCorrectly() {
    composeTestRule.setContent {
        DrawToolbar(/* 参数 */)
    }
    // 断言
}
```

2. **仪器化测试**
```kotlin
@RunWith(AndroidJUnit4::class)
class DrawAnywhereInstrumentationTest {
    @Test
    fun testDrawing_onRealDevice() {
        // 在实际设备/模拟器上测试
    }
}
```

## 故障排除

### 常见问题

1. **Robolectric 测试未运行**
   - 确保 build.gradle 中 `isIncludeAndroidResources = true`
   - 检查 `@Config` 注解中的 SDK 版本
   - 验证 Robolectric 依赖已添加

2. **MockK 验证失败**
   - 对模拟使用 `relaxed = true`（如果不需要模拟所有方法）
   - 确保协程使用测试调度器
   - 为异步操作调用 `testDispatcher.scheduler.advanceUntilIdle()`

3. **覆盖率报告为空**
   - 确保 debug 构建类型中 `enableUnitTestCoverage = true`
   - 生成覆盖率前运行 `./gradlew clean`
   - 检查测试是否实际执行

4. **协程测试挂起**
   - 始终使用 `StandardTestDispatcher` 或 `UnconfinedTestDispatcher`
   - 调用 `advanceUntilIdle()` 或 `runCurrent()` 执行协程
   - 设置主调度器：`Dispatchers.setMain(testDispatcher)`

## 总结

### 测试统计

- **测试文件总数**: 6 个新测试文件 + 1 个现有文件
- **测试用例总数**: 110+ 个独立测试
- **测试框架**: JUnit 4, MockK, Robolectric
- **覆盖率工具**: JaCoCo
- **测试类别**:
  - 纯单元测试: 34 个测试
  - MockK 测试: 50+ 个测试
  - Robolectric 测试: 27+ 个测试

### 主要成就

✅ 核心业务逻辑的全面测试覆盖  
✅ MockK 集成用于依赖隔离  
✅ Robolectric 设置用于 Android 框架测试  
✅ JaCoCo 配置用于覆盖率报告  
✅ 协程和 Flow 测试  
✅ 边界情况和错误场景覆盖  
✅ 组织良好的测试架构  

### 下一步

1. 运行测试并验证全部通过：`./gradlew test`
2. 生成覆盖率报告：`./gradlew testDebugUnitTestCoverage`
3. 查看覆盖率 HTML 报告
4. 为视觉组件添加 Compose UI 测试
5. 为真实设备场景添加仪器化测试
6. 设置 CI/CD 集成进行自动化测试
7. 在 build.gradle 中配置覆盖率阈值

---

**文档版本**: 1.0  
**最后更新**: 2026-05-19  
**作者**: AI Assistant  
**项目**: DrawAnywhere
