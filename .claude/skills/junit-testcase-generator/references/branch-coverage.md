# Branch Coverage Patterns

## Table of Contents

- [Branch Coverage Strategy](#branch-coverage-strategy)
- [If/Else Branches](#ifelse-branches)
- [Switch Statements](#switch-statements)
- [Try/Catch/Finally](#trycatchfinally)
- [Ternary Operators](#ternary-operators)
- [Optional and Null Checks](#optional-and-null-checks)
- [Loop Branches](#loop-branches)
- [Early Returns / Guard Clauses](#early-returns--guard-clauses)
- [Logical Operators (Short-Circuit)](#logical-operators-short-circuit)
- [Logger Guard Branches](#logger-guard-branches)
- [JaCoCo Configuration](#jacoco-configuration)
- [JaCoCo Coverage Verification Workflow](#jacoco-coverage-verification-workflow)

---

## Branch Coverage Strategy

For 100% branch coverage, every decision point must be tested for ALL outcomes.

### Branch Mapping Checklist

Before writing tests, map every branch in the source class:

```
1. Read the source class line by line
2. For EACH of these, record both/all paths:
   □ if (...) — true path AND false path (even if no explicit else)
   □ if/else if/else — each condition true, plus final else
   □ switch — every case label + default
   □ try/catch — success path + each catch block
   □ ternary (? :) — true evaluation + false evaluation
   □ && / || — short-circuit true + short-circuit false
   □ Optional.isPresent() — present + empty
   □ for/while — zero iterations + one+ iterations
   □ logger.isDebugEnabled() — true + false
   □ logger.isInfoEnabled() — true + false
   □ early return / guard clause — condition met + not met
3. Create one test per branch path minimum
```

---

## If/Else Branches

### Single If (No Else)

```java
// Source:
void process(String input) {
    if (input != null) {
        repository.save(input);
    }
    audit.log("processed");
}
```

```java
// Test TRUE path: input != null
@Test
void process_ShouldSave_WhenInputNotNull() {
    underTest.process("data");
    verify(repository).save("data");
    verify(audit).log("processed");
}

// Test FALSE path: input == null (skips the if block)
@Test
void process_ShouldSkipSave_WhenInputNull() {
    underTest.process(null);
    verify(repository, never()).save(any());
    verify(audit).log("processed");  // audit still called
}
```

### If/Else

```java
// Source:
String getStatus(int code) {
    if (code == 200) {
        return "OK";
    } else {
        return "ERROR";
    }
}
```

```java
@Test
void getStatus_ShouldReturnOK_WhenCode200() {
    assertEquals("OK", underTest.getStatus(200));
}

@Test
void getStatus_ShouldReturnError_WhenCodeNot200() {
    assertEquals("ERROR", underTest.getStatus(500));
}
```

### If/Else-If/Else Chain

```java
// Source:
String classify(int score) {
    if (score >= 90) return "A";
    else if (score >= 80) return "B";
    else if (score >= 70) return "C";
    else return "F";
}
```

```java
// Test EACH branch:
@ParameterizedTest
@CsvSource({"95, A", "85, B", "75, C", "65, F"})
void classify_ShouldReturnCorrectGrade(int score, String expected) {
    assertEquals(expected, underTest.classify(score));
}
```

### Nested If

```java
// Source:
void process(User user) {
    if (user != null) {
        if (user.isActive()) {
            activate(user);
        } else {
            deactivate(user);
        }
    }
}
```

```java
// Path 1: user=null (outer false)
@Test
void process_ShouldDoNothing_WhenUserNull() {
    underTest.process(null);
    // verify no interactions
}

// Path 2: user!=null, active=true (outer true, inner true)
@Test
void process_ShouldActivate_WhenUserActive() {
    User user = mock(User.class);
    when(user.isActive()).thenReturn(true);
    underTest.process(user);
    verify(underTest).activate(user);
}

// Path 3: user!=null, active=false (outer true, inner false)
@Test
void process_ShouldDeactivate_WhenUserInactive() {
    User user = mock(User.class);
    when(user.isActive()).thenReturn(false);
    underTest.process(user);
    verify(underTest).deactivate(user);
}
```

---

## Switch Statements

### Every Case + Default

```java
// Source:
String getDayType(DayOfWeek day) {
    switch (day) {
        case MONDAY: case TUESDAY: case WEDNESDAY:
        case THURSDAY: case FRIDAY:
            return "Weekday";
        case SATURDAY: case SUNDAY:
            return "Weekend";
        default:
            throw new IllegalArgumentException("Unknown day");
    }
}
```

```java
@ParameterizedTest
@EnumSource(value = DayOfWeek.class, names = {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"})
void getDayType_ShouldReturnWeekday(DayOfWeek day) {
    assertEquals("Weekday", underTest.getDayType(day));
}

@ParameterizedTest
@EnumSource(value = DayOfWeek.class, names = {"SATURDAY", "SUNDAY"})
void getDayType_ShouldReturnWeekend(DayOfWeek day) {
    assertEquals("Weekend", underTest.getDayType(day));
}

@Test
void getDayType_ShouldThrow_WhenNull() {
    assertThrows(NullPointerException.class, () -> underTest.getDayType(null));
}
```

### Switch with Fall-Through

Test each entry point separately to cover every case label.

---

## Try/Catch/Finally

### Success Path + Each Catch

```java
// Source:
String readFile(String path) {
    try {
        return fileService.read(path);
    } catch (FileNotFoundException e) {
        logger.warn("File not found: {}", path);
        return "default";
    } catch (IOException e) {
        logger.error("IO error reading: {}", path, e);
        throw new ServiceException("Read failed", e);
    } finally {
        audit.log("file-read-attempt");
    }
}
```

```java
// Path 1: Success (try block completes normally)
@Test
void readFile_ShouldReturnContent_WhenFileExists() throws Exception {
    when(fileService.read("test.txt")).thenReturn("content");
    assertEquals("content", underTest.readFile("test.txt"));
    verify(audit).log("file-read-attempt");
}

// Path 2: FileNotFoundException catch
@Test
void readFile_ShouldReturnDefault_WhenFileNotFound() throws Exception {
    when(fileService.read("missing.txt")).thenThrow(new FileNotFoundException());
    assertEquals("default", underTest.readFile("missing.txt"));
    verify(logger).warn(eq("File not found: {}"), eq("missing.txt"));
    verify(audit).log("file-read-attempt");
}

// Path 3: IOException catch
@Test
void readFile_ShouldThrowServiceException_WhenIOError() throws Exception {
    when(fileService.read("bad.txt")).thenThrow(new IOException("disk error"));
    assertThrows(ServiceException.class, () -> underTest.readFile("bad.txt"));
    verify(audit).log("file-read-attempt");
}
```

### Try-with-Resources

```java
// Source:
void processStream(InputStream stream) {
    try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream))) {
        String line = reader.readLine();
        process(line);
    } catch (IOException e) {
        handleError(e);
    }
}
```

Test both the success path AND the IOException path. The resource close is automatic.

---

## Ternary Operators

### Both true and false evaluations

```java
// Source:
String getLabel(boolean isAdmin) {
    return isAdmin ? "Administrator" : "User";
}
```

```java
@Test
void getLabel_ShouldReturnAdmin_WhenIsAdmin() {
    assertEquals("Administrator", underTest.getLabel(true));
}

@Test
void getLabel_ShouldReturnUser_WhenNotAdmin() {
    assertEquals("User", underTest.getLabel(false));
}
```

### Nested Ternary

```java
// Source:
String getPriority(int level) {
    return level > 8 ? "CRITICAL" : level > 5 ? "HIGH" : "LOW";
}
```

```java
// 3 paths: >8, 6-8, <=5
@ParameterizedTest
@CsvSource({"9, CRITICAL", "7, HIGH", "3, LOW"})
void getPriority_ShouldReturnCorrectLevel(int level, String expected) {
    assertEquals(expected, underTest.getPriority(level));
}
```

---

## Optional and Null Checks

```java
// Source:
String getUserName(Long id) {
    Optional<User> user = repository.findById(id);
    return user.map(User::getName).orElse("Unknown");
}
```

```java
// Path 1: Optional present
@Test
void getUserName_ShouldReturnName_WhenUserExists() {
    when(repository.findById(1L)).thenReturn(Optional.of(new User("John")));
    assertEquals("John", underTest.getUserName(1L));
}

// Path 2: Optional empty
@Test
void getUserName_ShouldReturnUnknown_WhenUserNotFound() {
    when(repository.findById(1L)).thenReturn(Optional.empty());
    assertEquals("Unknown", underTest.getUserName(1L));
}
```

---

## Loop Branches

### Zero Iterations vs One+ Iterations

```java
// Source:
int sumAll(List<Integer> numbers) {
    int total = 0;
    for (int n : numbers) {
        total += n;
    }
    return total;
}
```

```java
// Path 1: Empty list (zero iterations)
@Test
void sumAll_ShouldReturnZero_WhenEmptyList() {
    assertEquals(0, underTest.sumAll(Collections.emptyList()));
}

// Path 2: Non-empty list (one+ iterations)
@Test
void sumAll_ShouldReturnSum_WhenNonEmptyList() {
    assertEquals(6, underTest.sumAll(List.of(1, 2, 3)));
}
```

### While Loop with Break

```java
// Source:
String findFirst(List<Item> items, String type) {
    for (Item item : items) {
        if (item.getType().equals(type)) {
            return item.getName();  // early exit
        }
    }
    return null;  // no match
}
```

```java
// Path 1: Match found (early return)
@Test
void findFirst_ShouldReturnMatch_WhenFound() { ... }

// Path 2: No match (loop completes, returns null)
@Test
void findFirst_ShouldReturnNull_WhenNotFound() { ... }

// Path 3: Empty list
@Test
void findFirst_ShouldReturnNull_WhenEmptyList() { ... }
```

---

## Early Returns / Guard Clauses

```java
// Source:
Result process(Request request) {
    if (request == null) return Result.error("null request");
    if (request.getData().isEmpty()) return Result.error("empty data");
    if (!validator.isValid(request)) return Result.error("invalid");

    // Main logic
    return service.execute(request);
}
```

```java
// Guard 1: null request
@Test
void process_ShouldReturnError_WhenRequestNull() {
    assertEquals("null request", underTest.process(null).getError());
}

// Guard 2: empty data
@Test
void process_ShouldReturnError_WhenDataEmpty() {
    Request req = new Request("");
    assertEquals("empty data", underTest.process(req).getError());
}

// Guard 3: invalid request
@Test
void process_ShouldReturnError_WhenInvalid() {
    Request req = new Request("data");
    when(validator.isValid(req)).thenReturn(false);
    assertEquals("invalid", underTest.process(req).getError());
}

// Happy path: all guards pass
@Test
void process_ShouldExecute_WhenAllGuardsPass() {
    Request req = new Request("data");
    when(validator.isValid(req)).thenReturn(true);
    when(service.execute(req)).thenReturn(Result.success());
    assertTrue(underTest.process(req).isSuccess());
}
```

---

## Logical Operators (Short-Circuit)

### AND (&&) — Both Conditions Must Be Tested

```java
// Source:
if (user != null && user.isActive()) { ... }
```

```java
// Path 1: user=null (short-circuits, second condition not evaluated)
// Path 2: user!=null, isActive=false
// Path 3: user!=null, isActive=true
```

### OR (||) — Both Conditions Must Be Tested

```java
// Source:
if (isAdmin || hasPermission(resource)) { ... }
```

```java
// Path 1: isAdmin=true (short-circuits, second condition not evaluated)
// Path 2: isAdmin=false, hasPermission=true
// Path 3: isAdmin=false, hasPermission=false
```

---

## Logger Guard Branches

See `references/infrastructure-mocking.md` for full logger mocking setup.

### Quick Reference

For EVERY `logger.isDebugEnabled()` or `logger.isInfoEnabled()` in source code:

```java
// TRUE path — logger enabled, log statement executes
@Test
void method_ShouldLogDebug_WhenDebugEnabled() {
    when(logger.isDebugEnabled()).thenReturn(true);
    underTest.method();
    verify(logger).debug(anyString(), any());
}

// FALSE path — logger disabled, log statement SKIPPED
@Test
void method_ShouldSkipDebugLog_WhenDebugDisabled() {
    when(logger.isDebugEnabled()).thenReturn(false);
    underTest.method();
    verify(logger, never()).debug(anyString(), any());
}
```

---

## JaCoCo Configuration

### Maven Plugin Setup

```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.11</version>
    <executions>
        <execution>
            <goals><goal>prepare-agent</goal></goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals><goal>report</goal></goals>
        </execution>
    </executions>
</plugin>
```

### Exclude Classes from Coverage (DTOs, Entities, Config)

```xml
<configuration>
    <excludes>
        <exclude>**/dto/**</exclude>
        <exclude>**/entity/**</exclude>
        <exclude>**/config/**</exclude>
        <exclude>**/model/**</exclude>
        <exclude>**/*Application.*</exclude>
    </excludes>
</configuration>
```

### Report Location

After running `mvn clean test jacoco:report`:
- HTML report: `target/site/jacoco/index.html`
- XML report: `target/site/jacoco/jacoco.xml`
- CSV report: `target/site/jacoco/jacoco.csv`

### Reading JaCoCo Branch Coverage

In the HTML report:
- **Green** = fully covered
- **Yellow** = partially covered (some branches missed)
- **Red** = not covered

Click on a class → method → line to see which branches are missed.

---

## JaCoCo Coverage Verification Workflow

```
1. Generate tests for class
2. Run: mvn clean test -Dtest=<TestClass> jacoco:report
3. Open target/site/jacoco/<package>/<ClassName>.html
4. Check "Branches" column:
   - If 100% → Done, move to next class
   - If < 100% → Click to see missed branches
5. For each missed branch:
   a. Identify the condition (if/else, switch, try/catch, etc.)
   b. Write a new test targeting that specific branch
   c. Re-run step 2
6. Repeat until 100% branch coverage
```

### Parsing JaCoCo XML for Automation

```
target/site/jacoco/jacoco.xml contains:
<counter type="BRANCH" missed="0" covered="24"/>
<counter type="LINE" missed="0" covered="45"/>

If missed > 0 for BRANCH, more tests needed.
```
