---
name: junit-testcase-generator
description: |
  Generates comprehensive JUnit 5 test cases with Mockito for Maven-based Java projects.
  Traverses source folders, generates tests for all classes including private/static methods,
  verifies compilation, fixes errors, and tracks progress for resumable generation.
  This skill should be used when users need to generate unit tests for Java projects,
  create test coverage for legacy code, or automate test case creation across multiple classes.
---

# JUnit Test Case Generator

Automated JUnit 5 + Mockito test generation for Maven projects with progress tracking and error correction.

## What This Skill Does

- Traverses Java source folders to identify classes needing tests
- Generates JUnit 5 test cases with Mockito mocking framework
- Tests private methods (via reflection) and static methods (via MockedStatic)
- Verifies compilation and fixes errors automatically
- Tracks progress to resume if interrupted

## What This Skill Does NOT Do

- Generate integration or end-to-end tests
- Test UI components or Spring controllers (use specialized tools)
- Replace manual test design for complex business logic

---

## Quick Start

```
User: Generate JUnit tests for src/main/java
```

The skill will:
1. Scan the source folder for Java classes
2. Check tracking file for previously generated tests
3. Generate tests for each class iteratively
4. Verify and fix any compilation issues
5. Update tracking file for resume capability

---

## Before Implementation

Gather context to ensure successful implementation:

| Source | Gather |
|--------|--------|
| **Codebase** | Project structure, existing test patterns, pom.xml configuration |
| **Conversation** | Source folder path, any exclusion patterns, specific classes to prioritize |
| **Skill References** | JUnit 5 patterns, Mockito usage, reflection techniques from `references/` |
| **User Guidelines** | Team naming conventions, test organization preferences |

---

## Workflow

### Phase 1: Initialize & Scan

```
1. Verify Maven project structure:
   - Check pom.xml exists in project root
   - Verify JUnit 5 and Mockito dependencies (add if missing)

2. Run: python scripts/scan_project.py <source_folder>
   - Discovers all Java classes
   - Loads existing tracking from .junit-generator-tracking.json
   - Outputs classes needing tests

3. Test location: src/test/java (mirror package structure from src/main/java)
```

### Phase 2: Iterative Generation

For EACH class needing tests:

```
1. Read the source class thoroughly
2. Analyze:
   - Public methods → Standard JUnit tests
   - Private methods → Reflection-based tests
   - Static methods → MockedStatic tests
   - Dependencies → Mock with Mockito
3. Generate test class following patterns in references/
4. Write test file to test directory
5. Update tracking file
```

### Phase 3: Verification & Correction

```
1. Compile tests:
   mvn test-compile -q

2. For each compilation error:
   - Parse error message
   - Read the failing test
   - Fix the issue (imports, assertions, mocking)
   - Re-compile

3. Run tests to check for logical errors:
   mvn test -Dtest=<TestClass>

4. For each test failure:
   - Review expected vs actual
   - Fix failing assertions if test logic is incorrect
   - Re-run: mvn test -Dtest=<TestClass>
```

### Phase 4: Track Progress

```
1. Update .junit-generator-tracking.json:
   {
     "generated": ["com.example.UserService", ...],
     "pending": ["com.example.OrderService", ...],
     "failed": {"com.example.BrokenClass": "reason"},
     "lastRun": "2025-01-15T10:30:00Z"
   }

2. On next run, skip classes in "generated" list
```

---

## Test Generation Patterns

### Standard Test Structure

```java
@ExtendWith(MockitoExtension.class)
class {ClassName}Test {

    @Mock
    private DependencyA dependencyA;

    @InjectMocks
    private {ClassName} underTest;

    @BeforeEach
    void setUp() {
        // Additional setup if needed
    }

    @Test
    @DisplayName("{methodName} should {expectedBehavior} when {condition}")
    void {methodName}_Should{Behavior}_When{Condition}() {
        // Arrange

        // Act

        // Assert
    }
}
```

### Private Method Testing (Reflection)

```java
@Test
void privateMethod_ShouldReturnExpected() throws Exception {
    // Access private method
    Method method = {ClassName}.class.getDeclaredMethod("privateMethodName", ParamType.class);
    method.setAccessible(true);

    // Invoke
    Object result = method.invoke(underTest, paramValue);

    // Assert
    assertEquals(expected, result);
}
```

### Static Method Testing (MockedStatic)

```java
@Test
void staticMethod_ShouldBehaveCorrectly() {
    try (MockedStatic<{ClassName}> mocked = mockStatic({ClassName}.class)) {
        // Setup static mock
        mocked.when(() -> {ClassName}.staticMethod(any()))
              .thenReturn(expectedValue);

        // Act - call code that uses static method

        // Assert
        mocked.verify(() -> {ClassName}.staticMethod(any()));
    }
}
```

### Edge Cases to Generate

| Category | Test Cases |
|----------|------------|
| **Null inputs** | Pass null, verify NullPointerException or handling |
| **Empty inputs** | Empty strings, empty collections |
| **Boundary values** | Min/max integers, empty/full collections |
| **Exception paths** | Verify exceptions thrown for invalid states |
| **Happy path** | Normal successful execution |

---

## Required Clarifications

Before generating, confirm:

| Clarification | Default | Notes |
|---------------|---------|-------|
| **Source folder** | `src/main/java` | Path to Java source |
| **Test folder** | `src/test/java` | Path for generated tests |
| **pom.xml location** | Project root | Must contain JUnit 5 + Mockito deps |
| **Exclusions** | None | Patterns to skip (e.g., `**/dto/**`, `**/entity/**`) |
| **Naming convention** | `{ClassName}Test` | Test class naming pattern |

---

## Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `scan_project.py` | Scan source folder, identify classes | `python scripts/scan_project.py <src_folder>` |
| `verify_tests.py` | Compile and verify generated tests | `python scripts/verify_tests.py <test_folder> --build-tool maven` |
| `tracking.py` | Manage progress tracking file | `python scripts/tracking.py status` |

---

## Error Handling

### Compilation Errors

| Error Type | Fix Strategy |
|------------|--------------|
| Missing import | Add import statement |
| Type mismatch | Correct assertion or mock return type |
| Method not found | Check method signature, update test |
| Access modifier | Use reflection for private members |

### Test Failures

| Failure Type | Fix Strategy |
|--------------|--------------|
| AssertionError | Review expected vs actual, fix assertion |
| NullPointerException | Add null checks or mock setup |
| MockitoException | Fix mock configuration |

---

## Output Checklist

Before completing generation for each class:

- [ ] All public methods have at least one test
- [ ] Private methods tested via reflection where valuable
- [ ] Static methods mocked appropriately
- [ ] Dependencies mocked (no real DB/network calls)
- [ ] Naming follows `{MethodName}_Should{Behavior}_When{Condition}`
- [ ] Test compiles successfully
- [ ] Test runs without failures
- [ ] Tracking file updated

---

## Resume Capability

If generation stops (context limit, error, user interrupt):

1. Run skill again with same source folder
2. Skill reads `.junit-generator-tracking.json`
3. Skips classes already in "generated" list
4. Continues with "pending" classes
5. Retries "failed" classes with fresh approach

---

## Maven Dependencies

Ensure pom.xml has these dependencies. Add if missing:

```xml
<dependencies>
    <!-- JUnit 5 -->
    <dependency>
        <groupId>org.junit.jupiter</groupId>
        <artifactId>junit-jupiter</artifactId>
        <version>5.10.0</version>
        <scope>test</scope>
    </dependency>

    <!-- Mockito Core -->
    <dependency>
        <groupId>org.mockito</groupId>
        <artifactId>mockito-core</artifactId>
        <version>5.8.0</version>
        <scope>test</scope>
    </dependency>

    <!-- Mockito JUnit 5 Integration -->
    <dependency>
        <groupId>org.mockito</groupId>
        <artifactId>mockito-junit-jupiter</artifactId>
        <version>5.8.0</version>
        <scope>test</scope>
    </dependency>
</dependencies>

<build>
    <plugins>
        <!-- Maven Surefire Plugin for running tests -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-surefire-plugin</artifactId>
            <version>3.2.5</version>
        </plugin>
    </plugins>
</build>
```

### Maven Commands Reference

| Command | Purpose |
|---------|---------|
| `mvn test-compile` | Compile test classes only |
| `mvn test` | Run all tests |
| `mvn test -Dtest=UserServiceTest` | Run specific test class |
| `mvn test -Dtest=UserServiceTest#methodName` | Run specific test method |
| `mvn test -Dtest=*ServiceTest` | Run tests matching pattern |
| `mvn clean test` | Clean and run all tests |
| `mvn test -DskipTests=false -Dmaven.test.failure.ignore=true` | Run tests, don't fail build |

---

## Reference Files

| File | Content |
|------|---------|
| `references/junit5-patterns.md` | JUnit 5 annotations, assertions, lifecycle |
| `references/mockito-patterns.md` | Mocking, stubbing, verification patterns |
| `references/reflection-testing.md` | Testing private/protected members |
| `references/test-design.md` | Boundary value, equivalence partitioning |
