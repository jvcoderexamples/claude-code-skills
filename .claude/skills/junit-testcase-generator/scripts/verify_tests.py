#!/usr/bin/env python3
"""Verify a generated JUnit test class using Maven.

Runs: mvn test -Dtest=<ClassName>
Parses surefire output and compilation errors.
Outputs JSON or human-readable summary.

Usage:
  python3 verify_tests.py --test-class <ClassName> [options]

Options:
  --test-class <name>     Fully-qualified or simple test class name (required)
  --project-root <path>   Project root containing pom.xml (default: .)
  --output <format>       json | summary  (default: summary)

Exit codes: 0 = all tests pass, 1 = failure or error
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def main():
    project_root = "."
    test_class   = None
    output_format = "summary"

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if   a == "--project-root": project_root  = args[i + 1]; i += 2
        elif a == "--test-class":   test_class    = args[i + 1]; i += 2
        elif a == "--output":       output_format = args[i + 1]; i += 2
        else: i += 1

    if not (Path(project_root) / "pom.xml").exists():
        print(f"Error: No pom.xml found at {project_root}.", file=sys.stderr)
        sys.exit(1)

    if not test_class:
        print("Error: --test-class is required.", file=sys.stderr)
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    success, raw_output = run_maven(project_root, "test", f"-Dtest={test_class}")
    results  = parse_surefire_output(raw_output)
    comp_errs = parse_compilation_errors(raw_output)

    if output_format == "json":
        print(json.dumps({
            "success":           success,
            "testClass":         test_class,
            "results":           results,
            "compilationErrors": [_enrich(e) for e in comp_errs],
            "output":            raw_output[:3000],
        }, indent=2))
    else:
        if success:
            total  = results.get("total", 0)
            passed = results.get("passed", 0)
            print(f"✅ PASSED: {test_class} — {passed}/{total} tests passed")
        else:
            print(f"❌ FAILED: {test_class}")
            if comp_errs:
                print("\nCompilation errors:")
                for e in comp_errs[:5]:
                    print(f"  {e.get('file','?')}:{e.get('line','?')}: {e.get('message','')}")
                    print(f"  → Suggestion: {_suggest(e)}")
            else:
                f    = results.get("failed", 0)
                errs = results.get("errors", 0)
                t    = results.get("total",  0)
                print(f"\n  Tests: {t} run, {f} failed, {errs} errors")
                for fail in results.get("failures", [])[:3]:
                    msg = (fail.get("message") or "")[:120]
                    print(f"  ✗ {fail.get('method','?')}: {msg}")

    sys.exit(0 if success else 1)


# ---------------------------------------------------------------------------
# Maven execution
# ---------------------------------------------------------------------------

def run_maven(project_root: str, *maven_args: str) -> tuple[bool, str]:
    is_win = sys.platform.startswith("win")
    cmd = (["cmd", "/c", "mvn"] if is_win else ["mvn"]) + list(maven_args)
    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        combined = result.stdout + result.stderr
        return result.returncode == 0, combined
    except subprocess.TimeoutExpired:
        return False, "Maven command timed out after 300 seconds."
    except FileNotFoundError:
        return False, "mvn not found. Ensure Maven is installed and on PATH."


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------

def parse_surefire_output(output: str) -> dict:
    results = {"total": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0, "failures": []}

    # Summary line: Tests run: X, Failures: Y, Errors: Z, Skipped: W
    m = re.search(
        r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)",
        output,
    )
    if m:
        total, failed, errors, skipped = (int(m.group(x)) for x in (1, 2, 3, 4))
        results.update({
            "total":   total,
            "failed":  failed,
            "errors":  errors,
            "skipped": skipped,
            "passed":  total - failed - errors - skipped,
        })

    # Individual failure details
    failures = []
    for fm in re.finditer(
        r"(\w+)\(([^)]+)\)\s+Time elapsed:.*?<<<\s*(FAILURE|ERROR)!\s*\n(.*?)(?=\n\n|\n\w+\(|$)",
        output,
        re.DOTALL,
    ):
        failures.append({
            "method":  fm.group(1),
            "class":   fm.group(2),
            "type":    fm.group(3),
            "message": fm.group(4).strip()[:500],
        })
    results["failures"] = failures
    return results


def parse_compilation_errors(output: str) -> list:
    errors: list[dict] = []
    seen: set[str] = set()

    # Format 1: [ERROR] /path/File.java:[line,col] error: message
    for m in re.finditer(
        r"\[ERROR\]\s*([^\:\[\]]+\.java):\[(\d+),(\d+)\]\s*(?:error:)?\s*(.+)",
        output, re.MULTILINE,
    ):
        key = f"{m.group(1).strip()}:{m.group(2)}"
        if key not in seen:
            seen.add(key)
            errors.append({"file": m.group(1).strip(), "line": int(m.group(2)),
                           "column": int(m.group(3)), "message": m.group(4).strip()})

    # Format 2: [ERROR] /path/File.java:line: message
    for m in re.finditer(
        r"\[ERROR\]\s*([^\:\[\]]+\.java):(\d+):\s*(?:error:)?\s*(.+)",
        output, re.MULTILINE,
    ):
        key = f"{m.group(1).strip()}:{m.group(2)}"
        if key not in seen:
            seen.add(key)
            errors.append({"file": m.group(1).strip(), "line": int(m.group(2)),
                           "column": 0, "message": m.group(3).strip()})

    return errors


def _enrich(error: dict) -> dict:
    return {**error, "suggestion": _suggest(error)}


def _suggest(error: dict) -> str:
    msg = error.get("message", "").lower()
    if "cannot find symbol" in msg:
        if "class"    in msg: return "Add missing import. Check if class is on classpath."
        if "method"   in msg: return "Verify method name/signature matches the source class."
        if "variable" in msg: return "Check variable name exists in scope."
    if "incompatible types"  in msg: return "Fix type mismatch. Check expected vs actual types."
    if "cannot be applied"   in msg: return "Method arguments don't match signature. Check types/count."
    if "private access"      in msg: return "Use reflection (getDeclaredMethod/getDeclaredField) for private members."
    if "not visible"         in msg: return "Member is not accessible. Use reflection or widen visibility."
    if "package does not exist" in msg: return "Add missing dependency to pom.xml."
    if "unreported exception"   in msg: return "Add 'throws' clause or wrap in try-catch."
    if "non-static" in msg and "static" in msg: return "Cannot access instance member from static context."
    if "unnecessarystubbingexception" in msg: return "Remove unused stub or annotate with @MockitoSettings(strictness=LENIENT)."
    return "Review error message and fix accordingly."


if __name__ == "__main__":
    main()
