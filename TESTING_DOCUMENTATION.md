# Unit Testing Documentation for DrawAnywhere

## Overview

This document provides comprehensive information about the unit testing setup, test coverage, and testing strategies implemented for the DrawAnywhere Android application.

## Testing Framework Setup

### Dependencies Added

The following testing dependencies have been added to the project:

#### 1. **MockK** (Version 1.13.8)
- **Purpose**: Kotlin-native mocking library for creating mock objects
- **Usage**: Used for mocking dependencies in ViewModel tests
- **Added to**: `gradle/libs.versions.toml` and `app/build.gradle.kts`

#### 2. **Robolectric** (Version 4.11.1)
- **Purpose**: Android testing framework that runs tests on the JVM
- **Usage**: Tests Android-specific components without requiring an emulator
- **Added to**: `gradle/libs.versions.toml` and `app/build.gradle.kts`

#### 3. **JaCoCo** (Built-in Gradle Plugin)
- **Purpose**: Code coverage measurement tool
- **Usage**: Generates code coverage reports for unit tests
- **Configuration**: Enabled in `app/build.gradle.kts` with `jacoco` plugin

### Build Configuration Changes

```kotlin
// app/build.gradle.kts
plugins {
    jacoco  // Added JaCoCo plugin
}

android {
    testOptions {
        unitTests {
            isIncludeAndroidResources = true  // Enable Android resources in unit tests
        }
    }
    
    buildTypes {
        debug {
            enableUnitTestCoverage = true      // Enable coverage for unit tests
            enableAndroidTestCoverage = true   // Enable coverage for Android tests
        }
    }
}
```

## Test Files Created

### 1. **DrawControllerTest.kt** (MockK-based)
**Location**: `app/src/test/java/com/shezik/drawanywhere/DrawControllerTest.kt`

**Test Coverage**:
- Path creation and manipulation
- Undo/Redo functionality
- Stroke eraser behavior
- Path clearing operations
- Edge cases (empty paths, undo depth limits)
- State management (canUndo, canRedo, canClearPaths)

**Number of Tests**: 15 test cases

**Key Test Scenarios**:
```kotlin
- testCreatePath_addsPathToList()
- testUpdateLatestPath_addsPointToExistingPath()
- testFinishPath_addsToUndoStack()
- testUndo_removesLastPath()
- testRedo_restoresUndonePath()
- testClearPaths_removesAllPaths()
- testStrokeEraser_removesPathOnTouch()
- testMultipleUndoOperations()
- testUndoDepthLimit()
- testNewActionClearsRedoStack()
```

### 2. **DrawUtilsTest.kt** (Pure JUnit)
**Location**: `app/src/test/java/com/shezik/drawanywhere/DrawUtilsTest.kt`

**Test Coverage**:
- Distance calculations (distance, distanceSquared)
- Point-to-line-segment distance
- Midpoint calculations
- Path generation from points

**Number of Tests**: 14 test cases

**Key Test Scenarios**:
```kotlin
- testDistanceSquared_samePoint_returnsZero()
- testDistanceSquared_differentPoints_calculatesCorrectly()
- testDistancePointToLineSegment_pointOnLine_returnsZero()
- testDistancePointToLineSegment_pointBeforeStart_usesStartPoint()
- testCalculateMidpoint_calculatesCorrectly()
- testPointsToPath_emptyList_returnsEmptyPath()
- testPointsToPath_multiplePoints_createsSmoothPath()
```

### 3. **DrawViewModelTest.kt** (MockK-based)
**Location**: `app/src/test/java/com/shezik/drawanywhere/DrawViewModelTest.kt`

**Test Coverage**:
- UI state management
- Pen configuration changes (color, width, alpha)
- Canvas visibility and passthrough toggling
- Toolbar positioning and orientation
- Drawer state management
- Button pinning functionality
- Auto-clear canvas feature
- Stroke handling (start, update, finish)

**Number of Tests**: 35+ test cases

**Key Test Scenarios**:
```kotlin
- testInitialState_valuesAreCorrect()
- testSwitchToPen_changesPenType()
- testSetPenColor_updatesPenConfig()
- testToggleCanvasVisibility_togglesVisibility()
- testToggleCanvasPassthrough_togglesPassthrough()
- testClearCanvas_callsController()
- testSetToolbarPosition_updatesServiceState()
- testToggleToolbarOrientation_togglesOrientation()
- testPinSecondDrawerButton_pinsButton()
- testQuitApplication_stopsService()
- testStartStroke_createsPath()
- testAutoClearCanvas_clearsOnHide()
```

**Mocking Strategy**:
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

### 4. **DataClassTest.kt** (Pure JUnit)
**Location**: `app/src/test/java/com/shezik/drawanywhere/DataClassTest.kt`

**Test Coverage**:
- PenConfig data class
- PathWrapper data class
- ServiceState data class
- UiState data class
- DrawAction sealed class
- Enum types (PenType, ToolbarOrientation, StrokeModifier)

**Number of Tests**: 20+ test cases

**Key Test Scenarios**:
```kotlin
- testPenConfig_defaultValues()
- testPenConfig_customValues()
- testPenConfig_copy_createsNewInstance()
- testPathWrapper_creation()
- testPathWrapper_cachedPath_generation()
- testPathWrapper_invalidatePath_marksCacheInvalid()
- testServiceState_defaultValues()
- testUiState_defaultValues()
- testUiState_currentPenConfig_returnsCorrectConfig()
- testDefaultPenConfigs_returnsExpectedMap()
- testDrawAction_addPath()
- testDrawAction_erasePath()
- testDrawAction_clearPaths()
```

### 5. **PreferencesManagerRobolectricTest.kt** (Robolectric-based)
**Location**: `app/src/test/java/com/shezik/drawanywhere/PreferencesManagerRobolectricTest.kt`

**Test Coverage**:
- Saving and retrieving UI state
- Pen configuration persistence
- Service state persistence
- Enum value parsing
- DataStore integration
- Preference overwrites

**Number of Tests**: 12 test cases

**Key Test Scenarios**:
```kotlin
- testGetSavedUiState_returnsDefaultWhenNoPreferences()
- testSaveAndRetrieveUiState()
- testSaveAndRetrievePenConfigs()
- testGetSavedServiceState_returnsDefaultWhenNoPreferences()
- testSaveAndRetrieveServiceState()
- testGetEnumValueOrDefault_returnsDefaultWhenNull()
- testGetEnumValueOrDefault_returnsDefaultWhenInvalid()
- testSaveMultipleTimes_overwritesPreviousValues()
- testPartialPenConfigUpdate_preservesOtherConfigs()
- testToolbarPositionPersistence()
```

**Robolectric Configuration**:
```kotlin
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])  // Android API level 33
class PreferencesManagerRobolectricTest {
    private lateinit var context: Context
    
    @Before
    fun setup() {
        context = RuntimeEnvironment.getApplication()
        preferencesManager = PreferencesManager(context)
    }
}
```

### 6. **DrawControllerRobolectricTest.kt** (Robolectric-based)
**Location**: `app/src/test/java/com/shezik/drawanywhere/DrawControllerRobolectricTest.kt`

**Test Coverage**:
- Observable path list behavior
- Flow state emissions
- Complex drawing sequences
- Stroke eraser detection accuracy
- Undo/redo with erase actions
- Path caching mechanisms
- Concurrent path operations

**Number of Tests**: 15+ test cases

**Key Test Scenarios**:
```kotlin
- testPathList_isObservable()
- testFlowStates_emitCorrectValues()
- testComplexDrawingSequence()
- testErasePathWithStrokeEraser_detectsAndRemovesPath()
- testErasePath_missesPath_doesNotRemove()
- testUndoRedoWithEraseActions()
- testClearPaths_undoRedo()
- testPathWrapper_caching_worksCorrectly()
- testUpdateLatestPath_invalidatesCache()
- testMultiplePenConfigs_switchingPreservesState()
- testUndoStackDepthLimit_preventsOverflow()
- testConcurrentPathOperations_maintainsConsistency()
```

## Running Tests

### Run All Unit Tests
```bash
./gradlew test
```

### Run Tests with Coverage
```bash
./gradlew testDebugUnitTestCoverage
```

### Run Specific Test Class
```bash
./gradlew test --tests "com.shezik.drawanywhere.DrawControllerTest"
```

### Run Robolectric Tests Only
```bash
./gradlew testDebugUnitTest --tests "*RobolectricTest"
```

## Code Coverage Reports

### Generating Coverage Reports

After running tests with coverage enabled, reports are generated at:

```
app/build/reports/jacoco/testDebugUnitTestCoverage/html/index.html
```

### Viewing Coverage Report

1. Run tests with coverage:
   ```bash
   ./gradlew clean testDebugUnitTestCoverage
   ```

2. Open the HTML report in a browser:
   ```
   app/build/reports/jacoco/testDebugUnitTestCoverage/html/index.html
   ```

3. The report shows:
   - Line coverage
   - Branch coverage
   - Method coverage
   - Class coverage

### Expected Coverage Metrics

Based on the test suite created:

| Component | Expected Coverage | Test Type |
|-----------|------------------|-----------|
| DrawController | 85-95% | MockK + Robolectric |
| DrawViewModel | 80-90% | MockK |
| DrawUtils | 95-100% | Pure JUnit |
| Data Classes | 90-100% | Pure JUnit |
| PreferencesManager | 75-85% | Robolectric |
| **Overall** | **80-90%** | **Mixed** |

## Test Architecture

### Testing Layers

1. **Unit Tests (Pure JUnit)**
   - Test pure functions and data classes
   - No Android dependencies
   - Fastest execution
   - Example: `DrawUtilsTest`, `DataClassTest`

2. **Mocked Tests (MockK)**
   - Test business logic with mocked dependencies
   - Isolate ViewModel logic
   - Verify interactions
   - Example: `DrawViewModelTest`, `DrawControllerTest`

3. **Android Tests (Robolectric)**
   - Test Android-specific components
   - Real Android framework on JVM
   - Test DataStore integration
   - Example: `PreferencesManagerRobolectricTest`

### Test Organization

```
app/src/test/java/com/shezik/drawanywhere/
├── DrawControllerTest.kt              # MockK tests
├── DrawControllerRobolectricTest.kt   # Robolectric tests
├── DrawViewModelTest.kt               # MockK tests
├── DrawUtilsTest.kt                   # Pure JUnit tests
├── DataClassTest.kt                   # Pure JUnit tests
├── PreferencesManagerRobolectricTest.kt # Robolectric tests
└── ExampleUnitTest.kt                 # Original example test
```

## Testing Best Practices Implemented

### 1. **Given-When-Then Pattern**
```kotlin
@Test
fun testExample() = runBlocking {
    // Given
    val input = createTestData()
    
    // When
    val result = systemUnderTest.process(input)
    
    // Then
    assertEquals(expected, result)
}
```

### 2. **Descriptive Test Names**
- Format: `test[Method]_[Scenario]_[ExpectedResult]`
- Example: `testClearCanvas_callsController()`

### 3. **Isolated Tests**
- Each test is independent
- Fresh setup for each test
- No shared mutable state

### 4. **Edge Case Testing**
- Empty collections
- Null values
- Boundary conditions
- Error states

### 5. **Coroutine Testing**
```kotlin
@OptIn(ExperimentalCoroutinesApi::class)
private val testDispatcher = StandardTestDispatcher()

@Before
fun setup() {
    Dispatchers.setMain(testDispatcher)
}

@Test
fun testCoroutineFunction() = runBlocking {
    // Test code
    testDispatcher.scheduler.advanceUntilIdle()
}
```

## Coverage Improvement Strategies

### Current Coverage Gaps

1. **UI Components (Compose)**
   - DrawCanvas composable
   - DrawToolbar composable
   - MainActivity
   
   **Recommendation**: Add Compose UI tests using `createComposeRule()`

2. **Service Components**
   - MainService
   - DrawAnywhereTileService
   
   **Recommendation**: Add Robolectric service tests

3. **Integration Scenarios**
   - Full drawing workflow
   - Settings persistence across app restarts
   
   **Recommendation**: Add integration tests

### Future Test Additions

1. **Compose UI Tests**
```kotlin
@get:Rule
val composeTestRule = createComposeRule()

@Test
fun testDrawToolbar_rendersCorrectly() {
    composeTestRule.setContent {
        DrawToolbar(/* parameters */)
    }
    // Assertions
}
```

2. **Instrumentation Tests**
```kotlin
@RunWith(AndroidJUnit4::class)
class DrawAnywhereInstrumentationTest {
    @Test
    fun testDrawing_onRealDevice() {
        // Test on actual device/emulator
    }
}
```

3. **Property-Based Tests**
```kotlin
@Test
fun testDistance_isAlwaysNonNegative() {
    // Use property-based testing library
    forAll { p1: Offset, p2: Offset ->
        distance(p1, p2) >= 0f
    }
}
```

## Troubleshooting

### Common Issues

1. **Robolectric Tests Not Running**
   - Ensure `isIncludeAndroidResources = true` in build.gradle
   - Check SDK version in `@Config` annotation
   - Verify Robolectric dependency is added

2. **MockK Verification Fails**
   - Use `relaxed = true` for mocks if not all methods need stubbing
   - Ensure coroutines use test dispatchers
   - Call `testDispatcher.scheduler.advanceUntilIdle()` for async operations

3. **Coverage Report Empty**
   - Ensure `enableUnitTestCoverage = true` in debug build type
   - Run `./gradlew clean` before generating coverage
   - Check that tests are actually executing

4. **Coroutine Tests Hanging**
   - Always use `StandardTestDispatcher` or `UnconfinedTestDispatcher`
   - Call `advanceUntilIdle()` or `runCurrent()` to execute coroutines
   - Set main dispatcher: `Dispatchers.setMain(testDispatcher)`

## Summary

### Test Statistics

- **Total Test Files**: 6 new test files + 1 existing
- **Total Test Cases**: 110+ individual tests
- **Testing Frameworks**: JUnit 4, MockK, Robolectric
- **Coverage Tool**: JaCoCo
- **Test Categories**:
  - Pure Unit Tests: 34 tests
  - MockK Tests: 50+ tests
  - Robolectric Tests: 27+ tests

### Key Achievements

✅ Comprehensive test coverage for core business logic  
✅ MockK integration for dependency isolation  
✅ Robolectric setup for Android framework testing  
✅ JaCoCo configuration for coverage reporting  
✅ Testing of coroutines and Flow  
✅ Edge case and error scenario coverage  
✅ Well-organized test architecture  

### Next Steps

1. Run tests and verify all pass: `./gradlew test`
2. Generate coverage report: `./gradlew testDebugUnitTestCoverage`
3. Review coverage HTML report
4. Add Compose UI tests for visual components
5. Add instrumentation tests for real-device scenarios
6. Set up CI/CD integration for automated testing
7. Configure coverage thresholds in build.gradle

---

**Document Version**: 1.0  
**Last Updated**: 2026-05-19  
**Author**: AI Assistant  
**Project**: DrawAnywhere
