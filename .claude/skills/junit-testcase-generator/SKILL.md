---
name: junit-testcase-generator
description: |
  Generates comprehensive JUnit 5 test cases with Mockito for Maven-based Java projects.
  Targets 100% code and branch coverage: all if/else, switch, try/catch, ternary, and
  conditional paths including logger guard checks (isDebugEnabled, isInfoEnabled).
  Mocks database calls, API calls, Kafka read/writes, and loggers.
  Traverses source folders, generates tests for all classes including private/static methods,
  verifies each test class with Maven (mvn test -Dtest=<ClassName>Test) and JaCoCo coverage,
  auto-fixes errors up to 3 retries, and persists progress in junit-test-cases-coverage.json
  for automatic cross-session resume.
  This skill should be used when users need to generate unit tests for Java projects,
  create test coverage for legacy code, or automate test case creation across multiple classes.
---

# JUnit Test Case Generator

Automated JUnit 5 + Mockito test generation for Maven projects targeting **100% branch coverage** with per-class Maven + JaCoCo verification and automatic cross-session resume.

## What This Skill Does

- **Plans first** — scans Java source folders, builds a complete inventory, and saves it to `junit-test-cases-coverage.json` before generating any tests
- Persists progress in `junit-test-cases-coverage.json` inside the project root — survives session restarts with **automatic resume** (no confirmation needed)
- Generates JUnit 5 test cases with Mockito mocking framework, one class at a time
- **Targets 100% branch coverage** — every if/else, switch case, try/catch, ternary, and conditional path
- **Mocks infrastructure** — database calls, API calls, Kafka producer/consumer, loggers
- **Tests logger guards** — `logger.isDebugEnabled()` and `logger.isInfoEnabled()` both true AND false paths
- Tests private methods (via reflection) and static methods (via MockedStatic)
- Validates each generated test with `mvn test -Dtest=<ClassNameTest>` (syntax + pass) **and** checks JaCoCo branch/instruction coverage
- Retries up to **3 times** per file; marks as `needs_manual_review` after 3 failed attempts
- Tracks error history per file so each retry benefits from previous failure context

## What This Skill Does NOT Do

- Generate integration or end-to-end tests
- Test UI components or Spring controllers (use specialized tools)
- Replace manual test design for complex business logic

---

## Allowed Commands (No Permission Prompts Required)

The following shell commands **must run without asking for user permission**:

| Command | Purpose |
|---------|---------|
| `cd` | Change working directory |
| `ls` | List directory contents |
| `find` | Find files by pattern |
| `grep` | Search file contents |
| `tail` | Read end of files (e.g., Maven output) |
| `mvn` | Run Maven goals (compile, test, verify) |

All other tool calls (Edit, Write, Bash for other commands) follow normal permission rules.

> **Note**: The `scripts/` directory contains Python and Java equivalents for file scanning (`scan_project`), progress tracking (`tracking`), and Maven output parsing (`verify_tests`). Requires **Python ≥ 3.8** or **Java 11+**. They are retained as an alternative for users who prefer scripted operation, but the default workflow uses direct shell commands above.

---

## Quick Start

```
User: Generate JUnit tests for src/main/java
User: Resume JUnit test case generation
```

On every invocation: check for `junit-test-cases-coverage.json` → auto-resume if found, otherwise ask 2 clarifying questions → scan → generate → verify (Maven + JaCoCo) → update JSON. See Step 0 below for the full decision tree.

---

## Step 0: New Session vs. Resume Detection (MANDATORY FIRST STEP)

**Before anything else**, check for `junit-test-cases-coverage.json` in the project root:

```bash
# Run without asking permission:
ls junit-test-cases-coverage.json 2>/dev/null && echo "EXISTS" || echo "NOT_FOUND"
```

### If `junit-test-cases-coverage.json` EXISTS → Auto-Resume Flow

1. Read the file silently.
2. Display a concise progress summary:

```
📋 Resuming junit-test-cases-coverage.json
   ✅ completed: 12  |  🔄 in_progress: 1  |  ⏳ pending: 8  |  ⚠️  needs_manual_review: 0

Resuming from: com.example.PaymentService
```

3. **Immediately begin processing** the first `in_progress` file, or the first `pending` file if none are `in_progress`. Do NOT ask the user for confirmation.

### If `junit-test-cases-coverage.json` does NOT exist → Fresh Start Flow

Go to **Step 1: Ask Clarifying Questions**.

---

## Step 1: Ask Clarifying Questions (MANDATORY for Fresh Start)

Ask questions in **two waves**. Do not send all questions at once.

### Wave 1 — Required (always ask, cannot be inferred)

Ask these two questions in a single message and wait for the answer before proceeding:

1. **Source folder path** — Where is the Java source? (default: `src/main/java`)
2. **Exclusion patterns** — Any packages to skip entirely? e.g., `**/dto/**`, `**/entity/**`, `**/config/**` (default: none)

If the user does not answer a question, apply the stated default and proceed.

### Wave 2 — Optional (ask only if not auto-detectable)

Before sending Wave 2, **scan pom.xml and `src/test/java`** to infer answers (use `grep` — no permission needed):

- **Logger framework** — check pom.xml for `slf4j`, `log4j`, `logback` deps → skip if found
- **Kafka usage** — check pom.xml for `spring-kafka` or `kafka-clients` → skip if found
- **Database layer** — check pom.xml for `spring-data-jpa`, `mybatis`, `spring-jdbc` → skip if found
- **External API clients** — check pom.xml for `spring-web`, `openfeign`, `spring-webflux` → skip if found
- **Existing test patterns** — scan `src/test/java` for existing test class structure → skip if tests exist

Only ask Wave 2 questions that **could not** be answered by scanning. If all are inferable, skip Wave 2 entirely.

If Wave 2 is needed, ask remaining questions as a single follow-up message:

3. **Logger framework** — SLF4J+Log4j2, SLF4J+Logback, or other? (default: SLF4J+Log4j2)
4. **Existing test patterns** — Should generated tests follow an existing naming or structure convention?
5. **Priority classes** — Any specific classes to generate tests for first? (default: scan order)

If the user does not answer, apply the stated default and proceed.

---

## Before Implementation

Gather context before generating any tests:

| Source | Gather |
|--------|--------|
| **Codebase** | pom.xml deps (logger/Kafka/DB/HTTP framework), existing test structure in `src/test/java` |
| **Conversation** | Source folder path, exclusion patterns, priority classes |
| **Skill References** | `references/branch-coverage.md` — read for every class; `references/infrastructure-mocking.md` — read when DB/API/Kafka/Logger detected |
| **User Guidelines** | Team naming conventions, test organization preferences from CLAUDE.md if present |

---

## Phase 1: Plan — Initialize `junit-test-cases-coverage.json`

**This phase runs once, before any test generation begins.**

### 1.1 Scan Source Files

Use `find` (no permission needed) to discover all Java source files:

```bash
# Find all Java source files, excluding interfaces and generated code
find <source_folder> -name "*.java" -not -name "package-info.java" -not -name "module-info.java" | sort
```

For each discovered file, determine:
- **className** — simple class name (e.g., `UserService`)
- **fqn** — fully qualified name (e.g., `com.example.UserService`)
- **testFile** — expected test file path (e.g., `src/test/java/com/example/UserServiceTest.java`)
- **hasExistingTest** — whether the test file already exists (`ls` to check)
- **isInterface** — skip interfaces (`grep -l "^public interface\|^\s*interface " <file>`)
- **status** — `completed` if test file exists and was previously tracked; `pending` otherwise

### 1.2 Create `junit-test-cases-coverage.json`

Write the planning file to the project root before starting any generation:

```json
{
  "lastUpdated": "<ISO-8601-timestamp>",
  "sourceFolder": "src/main/java",
  "totalClasses": <N>,
  "processedClasses": 0,
  "summary": {
    "totalCompleted": 0,
    "totalInProgress": 0,
    "totalPending": <N>,
    "totalNeedsManualReview": 0
  },
  "classes": [
    {
      "className": "UserService",
      "fqn": "com.example.UserService",
      "testFile": "src/test/java/com/example/UserServiceTest.java",
      "status": "pending",
      "branchCoverage": null,
      "instructionsCoverage": null,
      "retryCount": 0,
      "lastError": null,
      "notes": null
    }
  ]
}
```

**Field definitions:**

| Field | Type | Description |
|-------|------|-------------|
| `className` | string | Simple class name |
| `fqn` | string | Fully qualified class name |
| `testFile` | string | Relative path to the test file |
| `status` | enum | `pending`, `in_progress`, `completed`, `failed`, `needs_manual_review` |
| `branchCoverage` | string\|null | JaCoCo branch coverage % (e.g., `"85%"`) — set after verification |
| `instructionsCoverage` | string\|null | JaCoCo instruction coverage % (e.g., `"92%"`) — set after verification |
| `retryCount` | int | Number of failed generation attempts |
| `lastError` | string\|null | First 400 chars of the most recent error |
| `notes` | string\|null | Optional notes about skipped classes or special handling |

### 1.3 Report to User

```
📋 Plan created: junit-test-cases-coverage.json
   Total classes found: 48
   Already have tests:  12 (marked as in_progress for coverage verification)
   Pending generation:  36

Starting test generation...
```

### 1.4 Add Missing pom.xml Dependencies

Check for and add JUnit 5, Mockito, Surefire, JaCoCo if absent. Use `grep` to check pom.xml first.

---

## Phase 2: Generate — One Class at a Time

Process files in this order:
1. `in_progress` files first (incomplete from prior session)
2. `pending` files in scan order
3. Skip `completed` and `needs_manual_review` files

For **EACH** file:

```
1. Update status to "in_progress" in junit-test-cases-coverage.json
   (Write tool — direct JSON edit)

2. Read the source class thoroughly (Read tool)

3. Map ALL branches in the class — see `references/branch-coverage.md` for the full branch taxonomy
   (if/else, switch, try/catch, ternary, Optional, guard clauses, loops, logger guards).

4. Analyze dependencies and mock strategy — see `references/infrastructure-mocking.md` for patterns.
   Summary: public → JUnit, private → reflection, static → MockedStatic, DB/HTTP/Kafka/Logger → mock.

5. If retryCount > 0: review lastError before generating
   - Avoid repeating the same mistakes
   - Apply targeted fixes based on previous error messages

6. Generate test class following patterns in references/
   - See references/infrastructure-mocking.md for DB, API, Kafka, Logger patterns
   - See references/branch-coverage.md for all-branches coverage patterns

7. Write test file to test directory (Write tool)

8. Proceed to Phase 3 (Verification)
```

---

## Phase 3: Verify — Maven Test + JaCoCo Coverage

**Both steps are required before marking a class as `completed`.**

### Step 3a: Run Maven Tests

```bash
# No permission needed for mvn:
mvn test -Dtest=<ClassNameTest> 2>&1 | tail -40
```

Parse output for:
- `BUILD SUCCESS` → tests passed
- `BUILD FAILURE` → compilation error or test failure
- `Tests run: N, Failures: F, Errors: E` → test counts

### Step 3b: Read JaCoCo Coverage Report

After a successful Maven test run, read the JaCoCo CSV or XML report to extract coverage for the specific class:

```bash
# Check if JaCoCo report exists (CSV or XML):
find target/site/jacoco -name "jacoco.csv" -o -name "jacoco.xml" 2>/dev/null | head -1
```

Extract **branch coverage** and **instruction coverage** for the class under test. If the JaCoCo report is not generated automatically, run:

```bash
# Use 'clean' to ensure target/jacoco.exec contains only this test's data:
mvn clean test -Dtest=<ClassNameTest> jacoco:report 2>&1 | tail -20
```

> **Why `clean` is required**: JaCoCo's `jacoco:report` goal reads all accumulated data from `target/jacoco.exec`. Without `clean`, exec data from previous test runs accumulates, producing inflated or inaccurate per-class coverage numbers.

Then read the report:
```bash
grep "SimpleClassName" target/site/jacoco/jacoco.csv   # or jacoco.xml
```

### Step 3c: Retry Loop (max 3 attempts)

```
RETRY LOOP (max 3 attempts per file):

Attempt 1..3:
  a. Run Maven tests (Step 3a)

  b. If BUILD FAILURE or test failures:
     - Read the error output carefully
     - Apply targeted fix to the test file

     Fix strategy by error type:
     | Error Type                   | Fix Strategy                                      |
     |------------------------------|---------------------------------------------------|
     | Missing import               | Add correct import statement                      |
     | Type mismatch                | Correct assertion or mock return type             |
     | Method not found             | Check method signature, update test               |
     | Access modifier (private)    | Use reflection (getDeclaredMethod/Field)           |
     | AssertionError               | Review expected vs actual, fix assertion          |
     | NullPointerException         | Add null checks or mock setup                     |
     | MockitoException             | Fix mock configuration                            |
     | UnnecessaryStubbingException | Remove unused stub or add @MockitoSettings(LENIENT)|

     - Update retryCount + lastError in junit-test-cases-coverage.json
     - If retryCount < 3: go to next attempt
     - If retryCount == 3: mark as needs_manual_review, continue to next class

  c. If BUILD SUCCESS:
     - Read JaCoCo coverage (Step 3b)
     - Update junit-test-cases-coverage.json with branchCoverage + instructionsCoverage
     - Mark status as "completed"
     - Print: "✅ {ClassName} — {branchCoverage} branch / {instructionsCoverage} instruction"
     - Move to next file
```

After 3 failed attempts:
```
- Set status = "needs_manual_review"
- Set lastError = "<summarized error>"
- Print: "⚠️  {ClassName} — 3 retries exhausted. Marked for manual review."
- Continue to next file (do NOT block progress)
```

---

## Phase 4: Update `junit-test-cases-coverage.json` After Every File

Update the file **immediately** after every status change — not just at the end. See `references/progress-schema.md` for full field definitions.

### Update the summary counters after every change:

```json
"summary": {
  "totalCompleted": <count of completed>,
  "totalInProgress": <count of in_progress>,
  "totalPending": <count of pending>,
  "totalNeedsManualReview": <count of needs_manual_review>
},
"processedClasses": <completed + needs_manual_review>,
"lastUpdated": "<ISO-8601-timestamp>"
```

### Example completed entry:

```json
{
  "className": "UserService",
  "fqn": "com.example.UserService",
  "testFile": "src/test/java/com/example/UserServiceTest.java",
  "status": "completed",
  "branchCoverage": "87%",
  "instructionsCoverage": "93%",
  "retryCount": 1,
  "lastError": null,
  "notes": null
}
```

---

## Test Generation Patterns

See `references/junit5-patterns.md`, `references/mockito-patterns.md`, and `references/reflection-testing.md` for standard structure, private/static method patterns, and edge case tables.

### Logger Guard Testing (CRITICAL — inline for visibility)

```java
// Test 1: logger.isDebugEnabled() returns TRUE
@Test
void methodName_ShouldLogDebug_WhenDebugEnabled() {
    when(logger.isDebugEnabled()).thenReturn(true);
    underTest.methodName();
    verify(logger).debug(anyString(), any());
}

// Test 2: logger.isDebugEnabled() returns FALSE
@Test
void methodName_ShouldSkipDebugLog_WhenDebugDisabled() {
    when(logger.isDebugEnabled()).thenReturn(false);
    underTest.methodName();
    verify(logger, never()).debug(anyString(), any());
}
```

---

## Must Avoid (Anti-Patterns)

Never do the following in generated tests:

- **Real DB connections** — never use actual datasources, JPA entities backed by a live DB, or `@SpringBootTest` with a database context
- **Real HTTP calls** — never call external REST APIs or services; always mock `RestTemplate`, `WebClient`, `FeignClient`
- **Real Kafka I/O** — never connect to an actual broker; always mock `KafkaTemplate`, `KafkaProducer`, `KafkaConsumer`
- **`Thread.sleep()` in assertions** — use `verify()` with timeouts or `Awaitility` if async behavior must be tested
- **Mocking the class under test** — never `mock(UserService.class)` when `UserService` is the class being tested; use `@InjectMocks`
- **Shared mutable state between test methods** — all mocks reset between tests via `@ExtendWith(MockitoExtension.class)`; do not use `static` fields for test data
- **Real credentials or PII in test fixtures** — use placeholder values (`"test-user"`, `"dummy-password"`) never production secrets
- **Ignoring `UnnecessaryStubbingException`** — remove unused stubs; do not suppress by default with `LENIENT` unless the stub is conditionally needed
- **Logging sensitive values in test output** — never print actual passwords, tokens, or PII in assertion messages or `System.out` calls within tests
- **Instantiating abstract or final classes directly** — use a concrete inner subclass for abstract classes; use `MockedStatic` or refactor for final classes that cannot be mocked

---

## Output Checklist

Before marking a class as `completed`:

- [ ] **ALL branches covered** — every if/else, switch/default, try/catch, ternary
- [ ] All public methods have tests for every code path
- [ ] Private methods tested via reflection where valuable
- [ ] Static methods mocked appropriately
- [ ] **Logger guards tested** — isDebugEnabled/isInfoEnabled both true AND false
- [ ] **Database calls mocked** — no real DB connections in tests
- [ ] **API calls mocked** — no real HTTP calls in tests
- [ ] **Kafka mocked** — KafkaTemplate/Producer/Consumer all mocked
- [ ] **Loggers mocked** — Logger instance mocked for guard condition testing
- [ ] Naming follows `{MethodName}_Should{Behavior}_When{Condition}`
- [ ] `mvn test -Dtest=<ClassNameTest>` → BUILD SUCCESS
- [ ] JaCoCo coverage extracted and recorded in `junit-test-cases-coverage.json`
- [ ] `junit-test-cases-coverage.json` updated with `status: completed`

---

## Maven Commands Reference

| Command | Purpose |
|---------|---------|
| `mvn test -Dtest=UserServiceTest` | **Primary verification** — compile + run single test class |
| `mvn test -Dtest=UserServiceTest#methodName` | Run specific test method |
| `mvn clean test -Dtest=UserServiceTest jacoco:report` | Run test + generate JaCoCo report (`clean` required for accurate single-class coverage) |
| `mvn test` | Run entire test suite |
| `mvn clean test` | Clean and run all tests |
| `mvn test -DskipTests=false -Dmaven.test.failure.ignore=true` | Run tests, don't fail build |

All `mvn` commands run **without requesting user permission**.

---

## Maven Dependencies

Ensure pom.xml includes JUnit 5, Mockito Core, Mockito JUnit Jupiter, Maven Surefire Plugin, and **JaCoCo Maven Plugin**. Add if missing.

> **Version freshness**: Verify current versions on Maven Central before adding — do not assume versions embedded in `references/maven-setup.md` are current. See that file for full dependency XML, plugin configuration, and Spring Boot compatibility guidance.

---

## Official Documentation

| Library | URL | Use For |
|---------|-----|---------|
| JUnit 5 User Guide | https://junit.org/junit5/docs/current/user-guide/ | Annotations, assertions, extensions, lifecycle |
| Mockito Javadoc | https://javadoc.io/doc/org.mockito/mockito-core/latest/ | Mock, stub, verify API reference |
| Mockito Site | https://site.mockito.org/ | Best practices, FAQ, migration guides |
| Maven Surefire Plugin | https://maven.apache.org/surefire/maven-surefire-plugin/ | Test runner configuration, `-Dtest=` filtering |
| JaCoCo | https://www.jacoco.org/jacoco/trunk/doc/ | Coverage report format, branch coverage rules |

> If you encounter a Mockito or JUnit 5 pattern not covered in the reference files, fetch the relevant URL above before generating the test. Do not guess at API signatures.

---

## Reference Files

> **Tip**: To locate a specific pattern quickly: `grep -n "keyword" references/<file>.md` — e.g., `grep -n "MockedStatic" references/mockito-patterns.md`

| File | When to Read |
|------|--------------|
| `references/junit5-patterns.md` | JUnit 5 annotations, assertions, lifecycle |
| `references/mockito-patterns.md` | Mocking, stubbing, verification patterns |
| `references/reflection-testing.md` | Testing private/protected members |
| `references/test-design.md` | Boundary value, equivalence partitioning |
| `references/infrastructure-mocking.md` | **Database, API, Kafka, Logger mocking** — read when class has DB/API/Kafka/Logger deps |
| `references/branch-coverage.md` | **All-branches coverage patterns** — read for every class |
| `references/maven-setup.md` | Dependency XML, plugin config, version freshness note, Spring Boot compatibility |
| `references/progress-schema.md` | Full `junit-test-cases-coverage.json` schema, field definitions, annotated example |
| `references/scripts-guide.md` | Full argument reference for `scripts/` Python/Java alternatives (scan, tracking, verify) |
