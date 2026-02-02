#!/usr/bin/env python3
"""
Verify generated JUnit tests using Maven.
Compiles tests, runs them, and reports errors for correction.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def check_maven_project(project_root: str) -> bool:
    """Check if project is a Maven project."""
    pom_path = Path(project_root) / "pom.xml"
    return pom_path.exists()


def compile_tests(project_root: str) -> Tuple[bool, str]:
    """Compile tests using Maven."""
    cmd = ["mvn", "test-compile", "-q"]

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120,
            shell=True  # For Windows compatibility
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output
    except subprocess.TimeoutExpired:
        return False, "Compilation timed out"
    except Exception as e:
        return False, str(e)


def run_test(project_root: str, test_class: str) -> Tuple[bool, str, Dict]:
    """Run a specific test class with Maven."""
    cmd = ["mvn", "test", f"-Dtest={test_class}", "-q"]

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300,
            shell=True
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr

        # Parse test results
        test_results = parse_surefire_output(output)

        return success, output, test_results
    except subprocess.TimeoutExpired:
        return False, "Test execution timed out", {}
    except Exception as e:
        return False, str(e), {}


def run_all_tests(project_root: str) -> Tuple[bool, str, Dict]:
    """Run all tests with Maven."""
    cmd = ["mvn", "test", "-q"]

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=600,
            shell=True
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr

        test_results = parse_surefire_output(output)

        return success, output, test_results
    except subprocess.TimeoutExpired:
        return False, "Test execution timed out", {}
    except Exception as e:
        return False, str(e), {}


def parse_surefire_output(output: str) -> Dict:
    """Parse Maven Surefire output to extract test results."""
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "failures": []
    }

    # Parse summary line: Tests run: X, Failures: Y, Errors: Z, Skipped: W
    match = re.search(
        r'Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)',
        output
    )
    if match:
        results["total"] = int(match.group(1))
        results["failed"] = int(match.group(2))
        results["errors"] = int(match.group(3))
        results["skipped"] = int(match.group(4))
        results["passed"] = results["total"] - results["failed"] - results["errors"] - results["skipped"]

    # Extract individual failure details
    # Pattern: testMethodName(com.example.TestClass)  Time elapsed: X.XXX s  <<< FAILURE!
    failure_pattern = re.compile(
        r'(\w+)\(([^)]+)\)\s+Time elapsed:.*?<<<\s*(FAILURE|ERROR)!\s*\n(.*?)(?=\n\n|\n\w+\(|$)',
        re.DOTALL
    )
    for match in failure_pattern.finditer(output):
        results["failures"].append({
            "method": match.group(1),
            "class": match.group(2),
            "type": match.group(3),
            "message": match.group(4).strip()[:500]  # Limit message length
        })

    return results


def parse_compilation_errors(output: str) -> List[Dict]:
    """Parse Maven compilation errors."""
    errors = []

    # Maven compilation error pattern
    # [ERROR] /path/to/File.java:[line,col] error: message
    pattern = re.compile(
        r'\[ERROR\]\s*([^:\[\]]+\.java):\[(\d+),(\d+)\]\s*(?:error:)?\s*(.+)',
        re.MULTILINE
    )

    for match in pattern.finditer(output):
        errors.append({
            "file": match.group(1).strip(),
            "line": int(match.group(2)),
            "column": int(match.group(3)),
            "message": match.group(4).strip()
        })

    # Alternative pattern without column
    alt_pattern = re.compile(
        r'\[ERROR\]\s*([^:\[\]]+\.java):(\d+):\s*(?:error:)?\s*(.+)',
        re.MULTILINE
    )

    for match in alt_pattern.finditer(output):
        file_path = match.group(1).strip()
        # Avoid duplicates
        if not any(e["file"] == file_path and e["line"] == int(match.group(2)) for e in errors):
            errors.append({
                "file": file_path,
                "line": int(match.group(2)),
                "column": 0,
                "message": match.group(3).strip()
            })

    return errors


def categorize_error(error: Dict) -> str:
    """Categorize compilation error for fix suggestion."""
    message = error["message"].lower()

    if "cannot find symbol" in message:
        if "class" in message:
            return "missing_import"
        elif "method" in message:
            return "wrong_method_name"
        elif "variable" in message:
            return "wrong_variable"
    elif "incompatible types" in message:
        return "type_mismatch"
    elif "cannot be applied" in message:
        return "wrong_arguments"
    elif "is not visible" in message or "has private access" in message:
        return "access_modifier"
    elif "package does not exist" in message:
        return "missing_dependency"
    elif "unreported exception" in message:
        return "unhandled_exception"
    elif "cannot access" in message:
        return "missing_import"
    elif "non-static" in message and "static" in message:
        return "static_context"

    return "unknown"


def suggest_fix(error: Dict) -> str:
    """Suggest fix for compilation error."""
    category = categorize_error(error)

    suggestions = {
        "missing_import": "Add missing import statement. Check if class exists in classpath.",
        "wrong_method_name": "Verify method name matches source class. Check spelling and parameters.",
        "wrong_variable": "Check variable name exists in scope. May need to declare or rename.",
        "type_mismatch": "Fix type mismatch. Check expected vs actual types in assignment/return.",
        "wrong_arguments": "Method arguments don't match signature. Check parameter types and count.",
        "access_modifier": "Cannot access private member directly. Use reflection for testing.",
        "missing_dependency": "Add missing dependency to pom.xml.",
        "unhandled_exception": "Add throws clause or try-catch block.",
        "static_context": "Static method trying to access non-static member. Fix context.",
        "unknown": "Review error message and fix accordingly."
    }

    return suggestions.get(category, suggestions["unknown"])


def verify_test_file(
    test_file: Path,
    project_root: str,
    run_tests: bool = True
) -> Dict:
    """Verify a single test file."""

    # Extract test class name from file
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()

    package_match = re.search(r'package\s+([\w.]+)\s*;', content)
    class_match = re.search(r'class\s+(\w+)', content)

    if not class_match:
        return {
            "file": str(test_file),
            "status": "error",
            "message": "Could not parse test class name"
        }

    package = package_match.group(1) if package_match else ""
    class_name = class_match.group(1)
    full_class_name = f"{package}.{class_name}" if package else class_name

    result = {
        "file": str(test_file),
        "className": full_class_name,
        "status": "pending"
    }

    # Compile
    compile_ok, compile_output = compile_tests(project_root)

    if not compile_ok:
        errors = parse_compilation_errors(compile_output)
        # Filter errors for this file
        file_errors = [e for e in errors if class_name in e.get("file", "")]

        result["status"] = "compilation_error"
        result["errors"] = file_errors
        result["suggestions"] = [
            {"error": e, "fix": suggest_fix(e)} for e in file_errors
        ]
        return result

    result["compiled"] = True

    # Run tests if requested
    if run_tests:
        test_ok, test_output, test_results = run_test(project_root, full_class_name)

        if test_ok:
            result["status"] = "passed"
            result["testResults"] = test_results
        else:
            result["status"] = "test_failure"
            result["testResults"] = test_results
            result["output"] = test_output[:2000]  # Limit output size

    return result


def verify_all_tests(
    test_folder: str,
    project_root: str,
    run_tests: bool = True
) -> Dict:
    """Verify all test files in folder."""

    # Check Maven project
    if not check_maven_project(project_root):
        return {
            "status": "error",
            "message": f"No pom.xml found at {project_root}. This skill requires a Maven project."
        }

    test_path = Path(test_folder)
    if not test_path.exists():
        return {
            "status": "error",
            "message": f"Test folder does not exist: {test_folder}"
        }

    # Find all test files
    test_files = list(test_path.rglob("*Test.java"))

    results = {
        "buildTool": "maven",
        "totalTests": len(test_files),
        "verified": [],
        "compilationErrors": [],
        "testFailures": [],
        "passed": []
    }

    # First, do a full compile
    print("Compiling all tests with Maven...")
    compile_ok, compile_output = compile_tests(project_root)

    if not compile_ok:
        errors = parse_compilation_errors(compile_output)
        results["compilationErrors"] = [
            {"error": e, "suggestion": suggest_fix(e)} for e in errors
        ]
        results["status"] = "compilation_failed"
        results["rawOutput"] = compile_output[:5000]
        return results

    print("Compilation successful. Running tests...")

    # Verify each test file
    for test_file in test_files:
        print(f"  Verifying: {test_file.name}")
        verification = verify_test_file(
            test_file, project_root, run_tests
        )

        results["verified"].append(verification)

        if verification["status"] == "passed":
            results["passed"].append(verification["className"])
        elif verification["status"] == "compilation_error":
            results["compilationErrors"].append(verification)
        elif verification["status"] == "test_failure":
            results["testFailures"].append(verification)

    results["status"] = "complete"
    results["summary"] = {
        "total": len(test_files),
        "passed": len(results["passed"]),
        "compilationErrors": len(results["compilationErrors"]),
        "testFailures": len(results["testFailures"])
    }

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Verify generated JUnit tests using Maven"
    )
    parser.add_argument(
        "test_folder",
        nargs="?",
        default="src/test/java",
        help="Path to test folder (default: src/test/java)"
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root directory containing pom.xml"
    )
    parser.add_argument(
        "--compile-only",
        action="store_true",
        help="Only compile, don't run tests"
    )
    parser.add_argument(
        "--test-class",
        help="Run specific test class only"
    )
    parser.add_argument(
        "--output",
        choices=["json", "summary"],
        default="summary",
        help="Output format"
    )

    args = parser.parse_args()

    # Check Maven project
    if not check_maven_project(args.project_root):
        print(f"Error: No pom.xml found at {args.project_root}")
        print("This skill requires a Maven project.")
        sys.exit(1)

    if args.test_class:
        # Run specific test
        print(f"Running test: {args.test_class}")
        success, output, test_results = run_test(args.project_root, args.test_class)

        if args.output == "json":
            print(json.dumps({
                "success": success,
                "results": test_results,
                "output": output[:2000]
            }, indent=2))
        else:
            if success:
                print(f"PASSED: {args.test_class}")
            else:
                print(f"FAILED: {args.test_class}")
                print(output[:1000])
        sys.exit(0 if success else 1)

    results = verify_all_tests(
        test_folder=args.test_folder,
        project_root=args.project_root,
        run_tests=not args.compile_only
    )

    if args.output == "json":
        print(json.dumps(results, indent=2))
    else:
        print(f"\n=== Maven Test Verification Results ===")
        if "summary" in results:
            s = results["summary"]
            print(f"Total test files: {s['total']}")
            print(f"  Passed:             {s['passed']}")
            print(f"  Compilation errors: {s['compilationErrors']}")
            print(f"  Test failures:      {s['testFailures']}")

            if results["compilationErrors"]:
                print(f"\nCompilation Errors:")
                for ce in results["compilationErrors"][:5]:
                    if "errors" in ce:
                        for err in ce["errors"][:3]:
                            print(f"  - {err['file']}:{err['line']}: {err['message'][:80]}")
                    elif "error" in ce:
                        err = ce["error"]
                        print(f"  - {err['file']}:{err['line']}: {err['message'][:80]}")
                        print(f"    Suggestion: {ce.get('suggestion', 'N/A')}")

            if results["testFailures"]:
                print(f"\nTest Failures:")
                for tf in results["testFailures"][:5]:
                    print(f"  - {tf['className']}")
                    if "testResults" in tf and "failures" in tf["testResults"]:
                        for f in tf["testResults"]["failures"][:2]:
                            print(f"    {f['method']}: {f.get('message', 'N/A')[:60]}")
        else:
            print(f"Status: {results.get('status', 'unknown')}")
            if "message" in results:
                print(f"Message: {results['message']}")


if __name__ == "__main__":
    main()
