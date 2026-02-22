# Progress Schema Reference

Full schema for `.junit-progress.json`, written to the project root and updated after every file operation.

## Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `projectRoot` | string | Absolute path to the Maven project root |
| `sourceFolder` | string | Relative path to Java source (e.g., `src/main/java`) |
| `testFolder` | string | Relative path to test output (e.g., `src/test/java`) |
| `scannedAt` | ISO 8601 | Timestamp of the initial source scan |
| `lastUpdatedAt` | ISO 8601 | Timestamp of the most recent file status change |
| `summary` | object | Running counts by status |
| `files` | object | Per-class tracking, keyed by fully-qualified class name |

## File Entry Fields

| Field | Type | Description |
|-------|------|-------------|
| `sourceFile` | string | Relative path to source `.java` file |
| `testFile` | string | Relative path to generated test file |
| `status` | enum | `pending` \| `in_progress` \| `completed` \| `failed` \| `needs_manual_review` |
| `retryCount` | integer | Number of failed `mvn test` attempts (0–3) |
| `errorHistory` | array | One entry per failed attempt (see below) |
| `startedAt` | ISO 8601 \| null | When generation started for this file |
| `completedAt` | ISO 8601 \| null | When `mvn test` passed; null if not yet complete |

## Error History Entry Fields

| Field | Type | Description |
|-------|------|-------------|
| `attempt` | integer | Attempt number (1, 2, or 3) |
| `timestamp` | ISO 8601 | When this attempt ran |
| `errorType` | string | `compilation` or `test_failure` |
| `errorSummary` | string | First 500 characters of Maven error output |

## Full Example

```json
{
  "projectRoot": "/path/to/project",
  "sourceFolder": "src/main/java",
  "testFolder": "src/test/java",
  "scannedAt": "2025-01-15T10:00:00Z",
  "lastUpdatedAt": "2025-01-15T11:45:00Z",
  "summary": {
    "total": 15,
    "completed": 8,
    "in_progress": 1,
    "pending": 4,
    "needs_manual_review": 2
  },
  "files": {
    "com.example.UserService": {
      "sourceFile": "src/main/java/com/example/UserService.java",
      "testFile": "src/test/java/com/example/UserServiceTest.java",
      "status": "completed",
      "retryCount": 0,
      "errorHistory": [],
      "startedAt": "2025-01-15T10:05:00Z",
      "completedAt": "2025-01-15T10:12:00Z"
    },
    "com.example.BrokenUtil": {
      "sourceFile": "src/main/java/com/example/BrokenUtil.java",
      "testFile": "src/test/java/com/example/BrokenUtilTest.java",
      "status": "needs_manual_review",
      "retryCount": 3,
      "errorHistory": [
        {
          "attempt": 1,
          "timestamp": "2025-01-15T10:30:00Z",
          "errorType": "compilation",
          "errorSummary": "cannot find symbol: method processData(java.lang.String)..."
        },
        {
          "attempt": 2,
          "timestamp": "2025-01-15T10:35:00Z",
          "errorType": "test_failure",
          "errorSummary": "AssertionError: expected:<OK> but was:<FAILED>..."
        },
        {
          "attempt": 3,
          "timestamp": "2025-01-15T10:40:00Z",
          "errorType": "test_failure",
          "errorSummary": "NullPointerException at BrokenUtilTest.java:45..."
        }
      ],
      "startedAt": "2025-01-15T10:28:00Z",
      "completedAt": null
    }
  }
}
```

## Write Rules

- Write after **every** status change — never batch multiple file updates
- Never delete the file mid-session (it is the single source of truth)
- On fresh scan: preserve existing `completed` entries; overwrite only `pending`/`failed` entries for newly discovered classes
