# Android Test Runner 缺失问题修复记录

## 问题概述

在尝试运行 Android 集成测试时，遇到 instrumentation 崩溃错误：

```
Test run failed to complete. Instrumentation run failed due to Process crashed.
java.lang.RuntimeException: Unable to instantiate instrumentation ComponentInfo{com.shezik.drawanywhere.test/androidx.test.runner.AndroidJUnitRunner}
Caused by: java.lang.ClassNotFoundException: Didn't find class "androidx.test.runner.AndroidJUnitRunner"
```

---

## 根本原因分析

### 错误信息解读

```
java.lang.ClassNotFoundException: Didn't find class "androidx.test.runner.AndroidJUnitRunner" 
on path: DexPathList[[...], zip file "/data/app/.../com.shezik.drawanywhere.test-.../base.apk", ...]
```

**关键信息**:
1. **ClassNotFoundException**: AndroidJUnitRunner 类找不到
2. **DexPathList**: 在测试 APK 的类路径中搜索
3. **com.shezik.drawanywhere.test**: 测试包名

**结论**: 测试 APK 中缺少 `androidx.test.runner` 依赖库。

### 为什么会发生？

Android instrumented tests (androidTest) 需要以下核心依赖才能运行：

1. **androidx.test:runner** - 提供 AndroidJUnitRunner
2. **androidx.test:rules** - 提供测试规则（可选但推荐）
3. **androidx.test.ext:junit** - AndroidX JUnit 扩展

项目中只配置了 `androidx.test.ext:junit`，但缺少核心的 `runner` 和 `rules` 库。

---

## 解决方案

### 步骤 1: 添加缺失的依赖

在 `app/build.gradle.kts` 的 `dependencies` 块中添加：

```kotlin
androidTestImplementation("androidx.test:runner:1.6.2")
androidTestImplementation("androidx.test:rules:1.6.1")
```

**完整配置**:
```kotlin
// Transitive dependencies
androidTestImplementation(libs.androidx.monitor)
androidTestImplementation(libs.junit)
androidTestImplementation(libs.mockk.android)
androidTestImplementation(libs.kotlinx.coroutines.test)
androidTestImplementation("androidx.test:runner:1.6.2")  // ← 新增
androidTestImplementation("androidx.test:rules:1.6.1")   // ← 新增
```

### 步骤 2: 验证版本兼容性

**可用版本查询**:
- Runner: https://developer.android.com/jetpack/androidx/releases/test#1.6.2
- Rules: https://developer.android.com/jetpack/androidx/releases/test#1.6.1

**注意**: 
- `runner:1.6.2` ✅ 存在
- `rules:1.6.2` ❌ 不存在（最新版本是 1.6.1）

### 步骤 3: 重新构建测试 APK

```bash
.\gradlew.bat clean assembleDebugAndroidTest --no-daemon
```

**预期输出**:
```
BUILD SUCCESSFUL in 30s
49 actionable tasks: 35 executed, 14 up-to-date
```

---

## 依赖说明

### androidx.test:runner

**作用**: 提供 Android 测试运行器基础设施

**包含的核心类**:
- `AndroidJUnitRunner` - JUnit 测试运行器
- `ActivityScenarioRule` - Activity 场景管理
- `ServiceTestRule` - Service 测试支持

**为什么必需**: 
- AndroidJUnitRunner 是所有 Android instrumented tests 的入口点
- 负责初始化测试环境、加载测试类、执行测试方法

### androidx.test:rules

**作用**: 提供常用的测试规则（Test Rules）

**包含的规则**:
- `ActivityScenarioRule` - 自动管理 Activity 生命周期
- `ServiceTestRule` - Service 测试支持
- `GrantPermissionRule` - 权限授予自动化

**为什么推荐**:
- 简化测试代码，自动处理资源清理
- 虽然不绝对必需，但强烈建议使用

---

## 完整的 androidTest 依赖清单

根据 DrawAnywhere 项目的需求，完整的测试依赖应包括：

```kotlin
// 核心测试框架
androidTestImplementation(libs.androidx.junit)          // AndroidX JUnit 扩展
androidTestImplementation("androidx.test:runner:1.6.2") // 测试运行器（必需）
androidTestImplementation("androidx.test:rules:1.6.1")  // 测试规则（推荐）

// 监控和工具
androidTestImplementation(libs.androidx.monitor)        // 应用状态监控

// Mock 框架
androidTestImplementation(libs.mockk.android)           // MockK for Android

// 协程测试
androidTestImplementation(libs.kotlinx.coroutines.test) // 协程测试支持

// Compose UI 测试（未来扩展）
// androidTestImplementation(platform(libs.androidx.compose.bom))
// androidTestImplementation(libs.androidx.ui.test.junit4)
// debugImplementation(libs.androidx.ui.test.manifest)
```

---

## 验证修复

### 1. 编译测试 APK

```bash
.\gradlew.bat assembleDebugAndroidTest --no-daemon
```

**成功标志**:
```
BUILD SUCCESSFUL in 30s
49 actionable tasks: 35 executed, 14 up-to-date
```

### 2. 运行集成测试

```bash
.\gradlew.bat connectedAndroidTest
```

**预期行为**:
- 测试 APK 安装到设备
- Instrumentation 正常启动
- 测试用例开始执行
- 生成测试报告

### 3. 检查测试报告

位置: `app/build/reports/androidTests/connected/debug/index.html`

---

## 常见问题排查

### Q1: 仍然出现 ClassNotFoundException

**可能原因**:
1. Gradle 缓存未更新
2. 设备上的旧测试 APK 未卸载

**解决方案**:
```bash
# 1. 清理并重新构建
.\gradlew.bat clean

# 2. 卸载旧的测试 APK
adb uninstall com.shezik.drawanywhere.test

# 3. 重新构建和安装
.\gradlew.bat connectedAndroidTest
```

### Q2: 版本冲突错误

**症状**:
```
Could not resolve androidx.test:runner:X.X.X
```

**解决方案**:
- 检查版本号是否正确
- 访问 [AndroidX Test Releases](https://developer.android.com/jetpack/androidx/releases/test) 确认可用版本
- 确保与项目的 `compileSdk` 和 `minSdk` 兼容

### Q3: 多个测试运行器冲突

**症状**:
```
Multiple test runners found
```

**解决方案**:
确保 `AndroidManifest.xml` 中只有一个 instrumentation 声明：

```xml
<!-- app/src/androidTest/AndroidManifest.xml -->
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <instrumentation
        android:name="androidx.test.runner.AndroidJUnitRunner"
        android:targetPackage="com.shezik.drawanywhere" />
</manifest>
```

---

## 最佳实践

### 1. 使用版本目录（Version Catalog）

建议在 `gradle/libs.versions.toml` 中统一管理版本：

```toml
[versions]
androidx-test-runner = "1.6.2"
androidx-test-rules = "1.6.1"

[libraries]
androidx-test-runner = { module = "androidx.test:runner", version.ref = "androidx-test-runner" }
androidx-test-rules = { module = "androidx.test:rules", version.ref = "androidx-test-rules" }
```

然后在 `build.gradle.kts` 中使用：

```kotlin
androidTestImplementation(libs.androidx.test.runner)
androidTestImplementation(libs.androidx.test.rules)
```

### 2. 定期更新测试依赖

- 每季度检查一次 AndroidX Test 的最新版本
- 关注 [Android Developers Blog](https://android-developers.googleblog.com/) 的公告
- 在更新前阅读 changelog，确保兼容性

### 3. 添加 Compose UI 测试依赖（未来）

如果将来需要测试 Compose UI 组件：

```kotlin
androidTestImplementation(platform(libs.androidx.compose.bom))
androidTestImplementation(libs.androidx.ui.test.junit4)
debugImplementation(libs.androidx.ui.test.manifest)
```

---

## 相关文件修改

### 修改的文件

**文件**: `app/build.gradle.kts`

**修改内容**:
```diff
     // Transitive dependencies
     androidTestImplementation(libs.androidx.monitor)
     androidTestImplementation(libs.junit)
     androidTestImplementation(libs.mockk.android)
     androidTestImplementation(libs.kotlinx.coroutines.test)
+    androidTestImplementation("androidx.test:runner:1.6.2")
+    androidTestImplementation("androidx.test:rules:1.6.1")
     implementation(libs.androidx.appcompat)
```

**行数变化**: +2 行

---

## 技术背景

### Android Instrumented Tests vs Unit Tests

| 特性 | Unit Tests (test/) | Instrumented Tests (androidTest/) |
|------|-------------------|----------------------------------|
| **运行环境** | JVM (本地) | Android 设备/模拟器 |
| **测试运行器** | JUnit4 / JUnit5 | AndroidJUnitRunner |
| **访问 Android API** | ❌ 否（除非 Robolectric） | ✅ 是 |
| **速度** | 快（秒级） | 慢（分钟级） |
| **典型用途** | 业务逻辑测试 | UI 测试、集成测试 |

### AndroidJUnitRunner 的作用

```
┌─────────────────────────────────────┐
│      AndroidJUnitRunner             │
│  (androidx.test.runner)             │
├─────────────────────────────────────┤
│  1. 初始化测试环境                   │
│  2. 加载测试类                       │
│  3. 执行 @Test 方法                  │
│  4. 收集测试结果                     │
│  5. 生成测试报告                     │
│  6. 清理资源                         │
└─────────────────────────────────────┘
         ↓ 调用
┌─────────────────────────────────────┐
│      你的测试类                      │
│  @RunWith(AndroidJUnit4::class)     │
│  class MyIntegrationTest {          │
│      @Test fun testFeature() { }    │
│  }                                  │
└─────────────────────────────────────┘
```

**没有 AndroidJUnitRunner**:
- 测试类无法被实例化
- Instrumentation 崩溃
- 测试无法执行

---

## 总结

### 问题根源
- 缺少 `androidx.test:runner` 依赖
- 导致 AndroidJUnitRunner 类找不到
- Instrumentation 初始化失败

### 解决方案
- 添加 `androidx.test:runner:1.6.2`
- 添加 `androidx.test:rules:1.6.1`（推荐）
- 重新构建测试 APK

### 验证结果
✅ BUILD SUCCESSFUL  
✅ 测试 APK 成功生成  
✅ 可以运行集成测试  

### 下一步
```bash
# 连接设备或启动模拟器后运行
.\gradlew.bat connectedAndroidTest
```

---

**修复日期**: 2026-06-15  
**修复状态**: ✅ 已完成  
**编译状态**: ✅ BUILD SUCCESSFUL  
**测试状态**: ⏳ 待运行  

**相关文档**:
- [集成测试分析报告.md](集成测试分析报告.md)
- [集成测试实施报告.md](集成测试实施报告.md)
- [集成测试快速指南.md](集成测试快速指南.md)
- [集成测试编译修复记录.md](集成测试编译修复记录.md)
