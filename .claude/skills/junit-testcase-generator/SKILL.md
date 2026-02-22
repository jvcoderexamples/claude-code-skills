---
name: junit-testcase-generator
description: |
  Generates comprehensive JUnit 5 test cases with Mockito for Maven-based Java projects.
  Targets 100% code and branch coverage: all if/else, switch, try/catch, ternary, and
  conditional paths including logger guard checks (isDebugEnabled, isInfoEnabled).
  Mocks database calls, API calls, Kafka read/writes, and loggers.
  Traverses source folders, generates tests for all classes including private/static methods,
  verifies each test class with Maven (mvn test -Dtest=<ClassName>Test), auto-fixes errors
  up to 3 retries, and persists progress in .junit-progress.json for cross-session resume.
  This skill should be used when users need to generate unit tests for Java projects,
  create test coverage for legacy code, or automate test case creation across multiple classes.
---

# JUnit Test Case Generator

Automated JUnit 5 + Mockito test generation for Maven projects targeting **100% branch coverage** with per-class Maven verification and cross-session progress tracking.

## What This Skill Does

- Scans Java source folders and builds a complete file inventory with per-file status tracking
- Persists progress in `.junit-progress.json` inside the project — survives session restarts
- On resume: shows a progress summary table and asks user to confirm before continuing
- Generates JUnit 5 test cases with Mockito mocking framework
- **Targets 100% branch coverage** — every if/else, switch case, try/catch, ternary, and conditional path
- **Mocks infrastructure** — database calls, API calls, Kafka producer/consumer, loggers
- **Tests logger guards** — `logger.isDebugEnabled()` and `logger.isInfoEnabled()` both true AND false paths
- Tests private methods (via reflection) and static methods (via MockedStatic)
- Verifies each generated test with `mvn test -Dtest=<ClassNameTest>` and auto-fixes errors
- Retries up to **3 times** per file; marks as `needs_manual_review` after 3 failed attempts
- Tracks error history per file so each retry benefits from previous failure context

## What This Skill Does NOT Do

- Generate integration or end-to-end tests
- Test UI components or Spring controllers (use specialized tools)
- Replace manual test design for complex business logic

---

## Quick Start

```
User: Generate JUnit tests for src/main/java
```

or, to resume a previous session:

```
User: Resume JUnit test case generation
```

The skill will:
1. **Check for `.junit-progress.json`** in the project root
2. If found → show progress summary and ask to confirm resume
3. If not found → ask clarifying questions, then scan and initialize tracking
4. Generate tests for each pending class covering **all branches**
5. Verify each class with `mvn test -Dtest=<ClassNameTest>`, fix errors (up to 3 retries)
6. Mark verified classes as `completed`; mark unresolvable classes as `needs_manual_review`
7. Update `.junit-progress.json` after every file

---

## Step 0: New Session vs. Resume Detection (MANDATORY FIRST STEP)

**Before anything else**, check for `.junit-progress.json` in the project root:

### If `.junit-progress.json` EXISTS → Resume Flow

1. Read the file and display a progress summary table:

```
┌─────────────────────────────────────────────┬───────────────────────┬────────┬────────────┐
│ Class (fully-qualified)                     │ Status                │Retries │ Last Error │
├─────────────────────────────────────────────┼───────────────────────┼────────┼────────────┤
│ com.example.UserService                     │ ✅ completed           │   0    │ —          │
│ com.example.OrderService                    │ ✅ completed           │   1    │ —          │
│ com.example.PaymentService                  │ 🔄 in_progress        │   1    │ NPE in ... │
│ com.example.NotificationService             │ ⏳ pending             │   0    │ —          │
│ com.example.BrokenUtil                      │ ⚠️  needs_manual_review│   3    │ cannot ... │
└─────────────────────────────────────────────┴───────────────────────┴────────┴────────────┘

Summary: 2 completed | 1 in_progress | 1 pending | 1 needs_manual_review
```

2. Ask the user:
   - "Continue from where we left off?" → resume from first `in_progress` or `pending` file
   - "Start a specific file?" → let user choose a class name to jump to
   - "Reset and start fresh?" → delete `.junit-progress.json` and re-scan

Do NOT proceed without user confirmation.

### If `.junit-progress.json` does NOT exist → Fresh Start Flow

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

Before sending Wave 2, **scan pom.xml and `src/test/java`** to infer answers:

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

Gather context to ensure successful implementation:

| Source | Gather |
|--------|--------|
| **Codebase** | Project structure, existing test patterns, pom.xml, logger framework, Kafka/DB usage |
| **Conversation** | Source folder path, exclusions, specific classes to prioritize |
| **Skill References** | JUnit 5 patterns, Mockito, infrastructure mocking, branch coverage from `references/` |
| **User Guidelines** | Team naming conventions, test organization preferences |

---

## Tool-Assisted Operations (Use Scripts — Not LLM — for These)

The `scripts/` directory contains Python and Java scripts for all deterministic operations. **Always use scripts instead of LLM reasoning** for: file scanning, progress tracking, and Maven output parsing.

### Runtime Detection (Run Once at Session Start)

Detect which runtime is available and store the result for the entire session:

```bash
# Prefer python3; fall back to Java
python3 --version 2>&1 && echo "RUNTIME=python" || echo "RUNTIME=java"
java --version 2>&1  # fallback check
```

Set `SKILL_DIR` to the skill's base directory (shown in the "Base directory for this skill:" header).

### Script Reference Table

| Operation | Python | Java | When to Use |
|-----------|--------|------|-------------|
| Scan source files | `python3 {SKILL_DIR}/scripts/scan_project.py` | `java --source 11 {SKILL_DIR}/scripts/ScanProject.java` | Phase 1: build class inventory |
| Manage progress file | `python3 {SKILL_DIR}/scripts/tracking.py` | `java --source 11 {SKILL_DIR}/scripts/Tracking.java` | After every status change |
| Verify test class | `python3 {SKILL_DIR}/scripts/verify_tests.py` | `java --source 11 {SKILL_DIR}/scripts/VerifyTests.java` | Phase 3: after writing each test |

**LLM is still needed for:** reading source classes, understanding business logic, generating test code, and fixing compilation/assertion errors.

---

## Workflow

### Phase 1: Initialize & Scan

```
1. Verify Maven project structure (Bash — not LLM):
   - Check pom.xml exists in project root

2. Run the source scanner script:

   # Python (preferred):
   python3 {SKILL_DIR}/scripts/scan_project.py <source_folder> \
       --test-folder <test_folder> \
       --exclude <pattern1> --exclude <pattern2> \
       --project-root <project_root> \
       --output json > /tmp/scan_result.json

   # Java fallback:
   java --source 11 {SKILL_DIR}/scripts/ScanProject.java <source_folder> \
       --test-folder <test_folder> \
       --exclude <pattern1> \
       --project-root <project_root> \
       --output json > /tmp/scan_result.json

   The script:
   - Walks the source tree, skips interfaces, package-info.java, module-info.java
   - Checks for existing test files
   - Checks pom.xml for JUnit 5, Mockito, Surefire, JaCoCo dependencies
   - Outputs structured JSON — no file writing, pure stdout

3. Initialize .junit-progress.json from scan output:

   # Python:
   python3 {SKILL_DIR}/scripts/tracking.py init \
       --project-root <project_root> \
       --scan-file /tmp/scan_result.json

   # Java:
   java --source 11 {SKILL_DIR}/scripts/Tracking.java init \
       --project-root <project_root> \
       --scan-file /tmp/scan_result.json

   This preserves any already-completed entries and creates pending entries
   for all classes that lack a test file.

4. Report to user:
   "Scanned X Java files. Y already have tests. Proceeding with Z files."

5. Add missing pom.xml dependencies (JUnit 5, Mockito, Surefire, JaCoCo) if
   the scan reported them absent. (LLM step — edit pom.xml.)
```

**Status values for each file:**

| Status | Meaning |
|--------|---------|
| `pending` | Not yet started |
| `in_progress` | Generation started but not verified |
| `completed` | Generated + Maven verified + all tests pass |
| `failed` | Current retry attempt failed, will be retried |
| `needs_manual_review` | 3 retries exhausted, cannot auto-fix |

### Phase 2: Iterative Generation (100% Branch Coverage)

Process files in this order:
1. `in_progress` files first (incomplete from prior session)
2. `pending` files in scan order
3. Skip `completed` and `needs_manual_review` files

For EACH file:

```
1. Update status to "in_progress" in .junit-progress.json
2. Update "startedAt" timestamp

3. Read the source class thoroughly
4. Map ALL branches in the class:
   - Every if/else (including single-if without else)
   - Every switch case + default
   - Every try/catch/finally block
   - Every ternary operator (both true and false)
   - Every Optional.isPresent()/isEmpty() path
   - Every early return / guard clause
   - Every loop (zero iterations + one+ iterations)
   - Every logger.isDebugEnabled() / logger.isInfoEnabled() (true AND false)

5. Analyze dependencies and mock strategy:
   - Public methods → Standard JUnit tests
   - Private methods → Reflection-based tests
   - Static methods → MockedStatic tests
   - Database calls (JPA, JDBC) → Mock repositories/datasources
   - API calls (RestTemplate, WebClient, Feign) → Mock HTTP clients
   - Kafka (KafkaTemplate, KafkaProducer, @KafkaListener) → Mock Kafka components
   - Loggers (SLF4J/Log4j2) → Mock Logger to test guard conditions

6. If retryCount > 0: review errorHistory entries before generating
   - Avoid repeating the same mistakes
   - Apply targeted fixes based on previous error messages

7. Generate test class following patterns in references/
   - See references/infrastructure-mocking.md for DB, API, Kafka, Logger patterns
   - See references/branch-coverage.md for all-branches coverage patterns

8. Write test file to test directory
9. Proceed to Phase 3 (Verification)
```

### Phase 3: Verification & Auto-Fix (3-Retry Loop)

Use the verify script to run Maven and parse results — do NOT run `mvn` directly and parse output by eye.

```
RETRY LOOP (max 3 attempts per file):

Attempt 1..3:
  a. Mark class as in_progress (script):

     # Python:
     python3 {SKILL_DIR}/scripts/tracking.py mark {FullyQualifiedClassName} in_progress \
         --project-root <project_root>

     # Java:
     java --source 11 {SKILL_DIR}/scripts/Tracking.java mark {FullyQualifiedClassName} in_progress \
         --project-root <project_root>

  b. Run verify script:

     # Python:
     python3 {SKILL_DIR}/scripts/verify_tests.py \
         --test-class {ClassNameTest} \
         --project-root <project_root> \
         --output json

     # Java:
     java --source 11 {SKILL_DIR}/scripts/VerifyTests.java \
         --test-class {ClassNameTest} \
         --project-root <project_root> \
         --output json

     The script runs: mvn test -Dtest={ClassNameTest}
     Parses surefire output + compilation errors into structured JSON.
     Exit code 0 = success, 1 = failure.

  c. If SUCCESS (exit code 0, "success": true):
     - Mark completed (script):
         tracking.py mark {FQN} completed --coverage "100%:100%"
     - Print: "✅ {ClassName} — verified in {N} attempt(s)"
     - Move to next file

  d. If FAILURE (exit code 1):
     - Script JSON output contains "compilationErrors" and/or "results.failures"
     - Use LLM to read the error details and apply the fix:

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
     | UnnecessaryStubbingException | Remove unused stub or switch to lenient()         |

     - Apply fix to the test file (LLM step)
     - Mark failed + record error (script):
         tracking.py mark {FQN} failed \
             --reason "<first 400 chars of error summary>" \
             --project-root <project_root>
     - If retryCount < 3: go to next attempt
     - If retryCount == 3: mark as needs_manual_review (script)

After 3 failed attempts:
     tracking.py mark {FQN} needs_manual_review \
         --reason "3 retries exhausted" --project-root <project_root>
     Print: "⚠️  {ClassName} — 3 retries exhausted. Marked for manual review."
     Continue to next file (do NOT block progress).
```

### Phase 4: Progress Persistence

**Use the tracking script after EVERY status change** — not just at the end.

```bash
# View current progress at any time:
python3 {SKILL_DIR}/scripts/tracking.py status --project-root <project_root>

# Get next batch of classes to process:
python3 {SKILL_DIR}/scripts/tracking.py next --batch 5 --project-root <project_root>

# Reset in_progress classes (e.g., after interrupted session):
python3 {SKILL_DIR}/scripts/tracking.py reset --target in_progress --project-root <project_root>
```

Key rules:
- Call `tracking.py mark` after every status change (never batch updates)
- Never delete `.junit-progress.json` mid-session — it is the single source of truth
- On fresh scan: `tracking.py init` preserves existing `completed` entries automatically

See `references/progress-schema.md` for the full JSON schema, field definitions, and a complete annotated example.

---

## Resume Flow Notes

When resuming (see Step 0 for the full decision tree and options):

- **"Retry `needs_manual_review` files?"** → run `tracking.py reset --target failed` then proceed normally
- **Before resuming an `in_progress` class**, re-read its source file — it may have changed since the last session

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
- [ ] `.junit-progress.json` updated with `status: completed`

---

## Maven Commands Reference

| Command | Purpose |
|---------|---------|
| `mvn test -Dtest=UserServiceTest` | **Primary verification** — compile + run single test class |
| `mvn test -Dtest=UserServiceTest#methodName` | Run specific test method |
| `mvn test` | Run entire test suite |
| `mvn clean test` | Clean and run all tests |
| `mvn test -DskipTests=false -Dmaven.test.failure.ignore=true` | Run tests, don't fail build |

---

## Maven Dependencies

Ensure pom.xml includes JUnit 5, Mockito Core, Mockito JUnit Jupiter, and Maven Surefire Plugin. Add if missing.

See `references/maven-setup.md` for full dependency XML, plugin configuration, version freshness note, and Spring Boot compatibility guidance.

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

| File | When to Read |
|------|--------------|
| `references/junit5-patterns.md` | JUnit 5 annotations, assertions, lifecycle |
| `references/mockito-patterns.md` | Mocking, stubbing, verification patterns |
| `references/reflection-testing.md` | Testing private/protected members |
| `references/test-design.md` | Boundary value, equivalence partitioning |
| `references/infrastructure-mocking.md` | **Database, API, Kafka, Logger mocking** — read when class has DB/API/Kafka/Logger deps |
| `references/branch-coverage.md` | **All-branches coverage patterns** — read for every class |
| `references/progress-schema.md` | Full `.junit-progress.json` schema, field definitions, annotated example |
| `references/maven-setup.md` | Dependency XML, plugin config, version freshness note, Spring Boot compatibility |
| `references/scripts-guide.md` | Full argument reference, JSON schemas, Java/Python examples for all 3 scripts |

---

## Scripts Reference

See `references/scripts-guide.md` for full argument reference, JSON output schemas, and Java/Python command examples for all three scripts (`scan_project`, `tracking`, `verify_tests`).
