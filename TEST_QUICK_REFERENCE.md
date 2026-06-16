# Quick Test Reference Guide

## Running Tests

### All Tests
```bash
./gradlew test
```

### Tests with Coverage
```bash
./gradlew clean testDebugUnitTestCoverage
```

### Specific Test Class
```bash
./gradlew test --tests "com.shezik.drawanywhere.DrawControllerTest"
```

### Only MockK Tests
```bash
./gradlew test --tests "*Test" --tests "!*RobolectricTest"
```

### Only Robolectric Tests
```bash
./gradlew testDebugUnitTest --tests "*RobolectricTest"
```

## Viewing Coverage Report

After running tests with coverage:

**Windows:**
```powershell
start app\build\reports\jacoco\testDebugUnitTestCoverage\html\index.html
```

**Linux/Mac:**
```bash
open app/build/reports/jacoco/testDebugUnitTestCoverage/html/index.html
```

## Test Files Summary

| File | Tests | Type | Coverage Target |
|------|-------|------|----------------|
| DrawControllerTest.kt | 15 | MockK | DrawController logic |
| DrawControllerRobolectricTest.kt | 15 | Robolectric | Android integration |
| DrawViewModelTest.kt | 35+ | MockK | ViewModel state management |
| DrawUtilsTest.kt | 14 | JUnit | Math utilities |
| DataClassTest.kt | 20+ | JUnit | Data classes & enums |
| PreferencesManagerRobolectricTest.kt | 12 | Robolectric | DataStore persistence |

**Total: 110+ test cases**

## Key Commands

```bash
# Clean and rebuild
./gradlew clean build

# Run only unit tests
./gradlew testDebugUnitTest

# Run only Android tests
./gradlew connectedAndroidTest

# Generate coverage report
./gradlew jacocoTestReport

# Check for test failures quickly
./gradlew test --continue

# Run tests in parallel (faster)
./gradlew test --parallel
```

## Troubleshooting

### Tests Not Found
```bash
./gradlew clean
./gradlew compileDebugKotlin
./gradlew test
```

### Coverage Report Empty
- Ensure `enableUnitTestCoverage = true` in debug build type
- Run `./gradlew clean` first
- Verify tests are executing (check test output)

### MockK Errors
```kotlin
// Use relaxed mocks when needed
mockk<MyClass>(relaxed = true)

// For coroutines, use test dispatcher
Dispatchers.setMain(StandardTestDispatcher())
```

### Robolectric Issues
```kotlin
// Ensure this annotation is present
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])

// And this in build.gradle
testOptions {
    unitTests.isIncludeAndroidResources = true
}
```

## Expected Output

Successful test run should show:
```
BUILD SUCCESSFUL in XXs
XX actionable tasks: XX executed
```

Test results location:
```
app/build/test-results/testDebugUnitTest/
```

Coverage results location:
```
app/build/reports/jacoco/testDebugUnitTestCoverage/
```
