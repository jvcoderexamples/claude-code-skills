# Scripts Reference Guide

All scripts live in `{SKILL_DIR}/scripts/`. Each operation has a **Python** and a **Java** version — functionally identical. Use whichever runtime is available.

## Runtime Detection (Run Once at Session Start)

```bash
# Prefer python3; fall back to Java
python3 --version 2>&1 && echo "RUNTIME=python" || echo "RUNTIME=java"
java --version 2>&1  # fallback check
```

**Requirements:** Python 3.8+ or Java 11+ (`--source 11`).
Set `SKILL_DIR` to the path shown in "Base directory for this skill:" at invocation time.

---

## scan_project.py / ScanProject.java

Scans the Maven source folder and returns the class inventory as JSON. **Stateless — writes nothing.**

```bash
# Python
python3 {SKILL_DIR}/scripts/scan_project.py src/main/java \
    --test-folder src/test/java \
    --exclude "**/dto/**" --exclude "**/entity/**" \
    --project-root . \
    --output json

# Java
java --source 11 {SKILL_DIR}/scripts/ScanProject.java src/main/java \
    --test-folder src/test/java \
    --exclude dto --exclude entity \
    --project-root . \
    --output json
```

**Output formats:** `json` (full inventory), `summary` (human-readable), `pending` (pending classes only)

**JSON fields per class:**
```
fullClassName, filePath, package, className, classType,
methods[], dependencies[], hasStaticMethods, hasPrivateMethods,
testFile, testFileExists, status ("pending"|"existing")
```

**JSON envelope fields:**
```
scannedAt, sourceFolder, testFolder, buildTool, mavenDependencies,
summary { totalClasses, pending, existingTests, withStaticMethods, withPrivateMethods },
classes[]
```

---

## tracking.py / Tracking.java

Manages `.junit-progress.json`. All commands print a confirmation message to stdout.

### Initialize from scan output

```bash
# Python
python3 {SKILL_DIR}/scripts/tracking.py init \
    --scan-file /tmp/scan_result.json --project-root .

# Java
java --source 11 {SKILL_DIR}/scripts/Tracking.java init \
    --scan-file /tmp/scan_result.json --project-root .
```

Preserves existing `completed` entries; creates `pending` entries for classes without test files.

### Show progress table

```bash
python3 {SKILL_DIR}/scripts/tracking.py status --project-root .
```

### Get next batch (returns JSON array of class names)

```bash
python3 {SKILL_DIR}/scripts/tracking.py next --batch 5 --project-root .
```

Returns `in_progress` classes first (resume interrupted work), then `pending` classes.

### Mark a class status

```bash
# Start work
python3 {SKILL_DIR}/scripts/tracking.py mark com.example.UserService in_progress

# Mark completed with coverage
python3 {SKILL_DIR}/scripts/tracking.py mark com.example.UserService completed \
    --coverage "100%:100%"

# Mark failed with error reason
python3 {SKILL_DIR}/scripts/tracking.py mark com.example.UserService failed \
    --reason "Cannot find symbol: KafkaProducer" --project-root .

# Mark for manual review
python3 {SKILL_DIR}/scripts/tracking.py mark com.example.UserService needs_manual_review \
    --reason "3 retries exhausted" --project-root .
```

**Status values:** `pending` | `in_progress` | `completed` | `failed` | `needs_manual_review`

**Class name matching:** Accepts full FQN (`com.example.UserService`) or suffix/substring (`UserService`). Errors if ambiguous.

### Reset classes

```bash
python3 {SKILL_DIR}/scripts/tracking.py reset --target failed --project-root .
python3 {SKILL_DIR}/scripts/tracking.py reset --target in_progress --project-root .
python3 {SKILL_DIR}/scripts/tracking.py reset --target all --project-root .
```

### Export full progress file

```bash
python3 {SKILL_DIR}/scripts/tracking.py export --project-root .
```

---

## verify_tests.py / VerifyTests.java

Runs `mvn test -Dtest=<Class>` and returns structured results. Exit code 0 = pass, 1 = fail.

```bash
# Python
python3 {SKILL_DIR}/scripts/verify_tests.py \
    --test-class UserServiceTest \
    --project-root . \
    --output json

# Java
java --source 11 {SKILL_DIR}/scripts/VerifyTests.java \
    --test-class UserServiceTest \
    --project-root . \
    --output json
```

**JSON output schema:**
```json
{
  "success": true,
  "testClass": "UserServiceTest",
  "results": {
    "total": 5,
    "passed": 5,
    "failed": 0,
    "errors": 0,
    "skipped": 0,
    "failures": [
      { "method": "...", "class": "...", "type": "FAILURE|ERROR", "message": "..." }
    ]
  },
  "compilationErrors": [
    { "file": "...", "line": 42, "column": 0, "message": "...", "suggestion": "..." }
  ],
  "output": "<first 3000 chars of mvn stdout+stderr>"
}
```

**Built-in fix suggestions** (`compilationErrors[].suggestion`):
- `cannot find symbol` → add import / check classpath / verify method signature
- `incompatible types` → fix type mismatch
- `private access` → use reflection (`getDeclaredMethod`/`getDeclaredField`)
- `package does not exist` → add dependency to pom.xml
- `UnnecessaryStubbingException` → remove unused stub or use `lenient()`

---

## LLM-Only Operations (No Script Available)

| Task | Why LLM is Needed |
|------|------------------|
| Read and understand source class | Semantic comprehension of business logic |
| Map all branch paths in source | Requires understanding conditional semantics |
| Generate test method bodies | Creative synthesis: mocks, assertions, edge cases |
| Fix compilation/assertion errors | Error interpretation + targeted code changes |
| Add pom.xml dependencies | Context-dependent XML editing |
