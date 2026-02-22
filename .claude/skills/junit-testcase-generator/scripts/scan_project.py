#!/usr/bin/env python3
"""Scan Maven Java project source folder and identify classes needing unit tests.

Stateless: reads source files, writes nothing. Output goes to stdout.

Usage:
  python3 scan_project.py [source_folder] [options]

Arguments:
  source_folder           Path to Java source folder (default: src/main/java)

Options:
  --test-folder <path>    Path to test folder (default: src/test/java)
  --exclude <pattern>     Substring to exclude from relative file paths (repeatable)
  --project-root <path>   Project root containing pom.xml (default: .)
  --output <format>       json | summary | pending  (default: summary)

Exit codes: 0 = success, 1 = error (missing pom.xml or source folder)
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    source_folder = "src/main/java"
    test_folder = "src/test/java"
    project_root = "."
    output_format = "summary"
    exclusions = []

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--test-folder":
            test_folder = args[i + 1]; i += 2
        elif a == "--exclude":
            exclusions.append(args[i + 1]); i += 2
        elif a == "--project-root":
            project_root = args[i + 1]; i += 2
        elif a == "--output":
            output_format = args[i + 1]; i += 2
        elif not a.startswith("--"):
            source_folder = a; i += 1
        else:
            i += 1

    pom_path = Path(project_root) / "pom.xml"
    if not pom_path.exists():
        print(f"Error: No pom.xml found at {project_root}. This skill requires a Maven project.",
              file=sys.stderr)
        sys.exit(1)

    deps = check_maven_dependencies(pom_path)
    classes = scan_source_files(source_folder, test_folder, exclusions)

    total         = len(classes)
    pending_count = sum(1 for c in classes if c["status"] == "pending")
    existing_count= sum(1 for c in classes if c["status"] == "existing")
    with_static   = sum(1 for c in classes if c["hasStaticMethods"])
    with_private  = sum(1 for c in classes if c["hasPrivateMethods"])

    if output_format == "json":
        print(json.dumps({
            "scannedAt":          datetime.now(timezone.utc).isoformat(),
            "sourceFolder":       source_folder,
            "testFolder":         test_folder,
            "buildTool":          "maven",
            "mavenDependencies":  deps,
            "summary": {
                "totalClasses":      total,
                "pending":           pending_count,
                "existingTests":     existing_count,
                "withStaticMethods": with_static,
                "withPrivateMethods":with_private,
            },
            "classes": classes,
        }, indent=2))

    elif output_format == "pending":
        pending = [c for c in classes if c["status"] == "pending"]
        print(json.dumps(pending, indent=2))

    else:  # summary
        print("\n=== Maven Project Scan Results ===")
        print(f"Project root:  {project_root}")
        print(f"Source folder: {source_folder}")
        print(f"Test folder:   {test_folder}")
        print("\nMaven Dependencies:")
        _yn = lambda ok, add: "Y" if ok else f"N  ({add})"
        print(f"  JUnit 5:  {_yn(deps.get('hasJunit5'),  'add junit-jupiter to pom.xml')}")
        print(f"  Mockito:  {_yn(deps.get('hasMockito'),  'add mockito-core to pom.xml')}")
        print(f"  Surefire: {_yn(deps.get('hasSurefire'), 'add maven-surefire-plugin')}")
        print(f"  JaCoCo:   {_yn(deps.get('hasJacoco'),   'add jacoco-maven-plugin')}")
        print(f"\nClasses Found: {total}")
        print(f"  Pending (no tests):   {pending_count}")
        print(f"  With existing tests:  {existing_count}")
        print(f"\nClasses with static methods:   {with_static}")
        print(f"Classes with private methods:  {with_private}")
        if pending_count > 0:
            print("\nRun with --output pending to list classes needing tests.")
            print("Run with --output json to get full class details.")


# ---------------------------------------------------------------------------
# Maven pom.xml inspection
# ---------------------------------------------------------------------------

def check_maven_dependencies(pom_path: Path) -> dict:
    try:
        content = pom_path.read_text(encoding="utf-8")
        return {
            "hasPom":      True,
            "hasJunit5":   "junit-jupiter" in content,
            "hasMockito":  "mockito-core" in content or "mockito-junit-jupiter" in content,
            "hasSurefire": "maven-surefire-plugin" in content,
            "hasJacoco":   "jacoco-maven-plugin" in content,
        }
    except OSError:
        return {"hasPom": False}


# ---------------------------------------------------------------------------
# Source folder walker
# ---------------------------------------------------------------------------

def scan_source_files(source_folder: str, test_folder: str, exclusions: list) -> list:
    source_path = Path(source_folder)
    if not source_path.exists():
        print(f"Error: Source folder does not exist: {source_folder}", file=sys.stderr)
        sys.exit(1)

    classes = []
    for java_file in sorted(source_path.rglob("*.java")):
        relative = str(java_file.relative_to(source_path))

        # Skip excluded paths (substring match on relative path)
        if any(exc in relative for exc in exclusions):
            continue

        # Skip package-info and module-info
        if java_file.stem in ("package-info", "module-info"):
            continue

        info = extract_class_info(java_file)
        if info is None:
            continue

        # Skip pure interfaces (no tests needed beyond integration)
        if info["classType"] == "interface":
            continue

        # Resolve expected test file
        pkg_dir = info["package"].replace(".", os.sep) if info["package"] else ""
        test_file_path = Path(test_folder) / pkg_dir / f"{info['className']}Test.java"
        test_file_str  = str(test_file_path).replace(os.sep, "/")

        info["testFile"]      = test_file_str
        info["testFileExists"]= test_file_path.exists()
        info["status"]        = "existing" if info["testFileExists"] else "pending"

        classes.append(info)

    return classes


# ---------------------------------------------------------------------------
# Class-level Java parser (regex-based, no external deps)
# ---------------------------------------------------------------------------

def extract_class_info(file_path: Path) -> dict | None:
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    # Package
    m = re.search(r"package\s+([\w.]+)\s*;", content)
    package = m.group(1) if m else ""

    # Primary type declaration
    m = re.search(
        r"(?:public\s+)?(?:abstract\s+)?(?:final\s+)?"
        r"(?:class|interface|enum|record)\s+(\w+)",
        content,
    )
    if not m:
        return None
    class_name     = m.group(1)
    full_class_name = f"{package}.{class_name}" if package else class_name

    # Classify type
    class_type = "class"
    if   re.search(rf"\binterface\s+{re.escape(class_name)}", content): class_type = "interface"
    elif re.search(rf"\benum\s+{re.escape(class_name)}",      content): class_type = "enum"
    elif re.search(rf"\brecord\s+{re.escape(class_name)}",    content): class_type = "record"
    elif re.search(rf"\babstract\s+class\s+{re.escape(class_name)}", content): class_type = "abstract"

    methods      = extract_methods(content, class_name)
    dependencies = extract_dependencies(content)
    has_static   = any(m2.get("isStatic") for m2 in methods)
    has_private  = any(m2.get("visibility") == "private" for m2 in methods)

    return {
        "filePath":          str(file_path).replace(os.sep, "/"),
        "package":           package,
        "className":         class_name,
        "fullClassName":     full_class_name,
        "classType":         class_type,
        "methods":           methods,
        "dependencies":      dependencies,
        "hasStaticMethods":  has_static,
        "hasPrivateMethods": has_private,
    }


def extract_methods(content: str, class_name: str) -> list:
    pattern = re.compile(
        r"(?P<visibility>public|private|protected)?\s*"
        r"(?P<static>static)?\s*"
        r"(?P<final>final)?\s*"
        r"(?P<returnType>[\w<>,\s\[\]]+)\s+"
        r"(?P<name>\w+)\s*"
        r"\((?P<params>[^)]*)\)\s*"
        r"(?:throws\s+(?P<throws>[\w,\s]+))?\s*\{",
        re.MULTILINE,
    )
    methods = []
    for m in pattern.finditer(content):
        method_name = m.group("name")
        return_type = (m.group("returnType") or "").strip()
        if return_type == method_name:
            continue  # constructor
        throws_str = m.group("throws") or ""
        methods.append({
            "name":       method_name,
            "visibility": m.group("visibility") or "package-private",
            "isStatic":   m.group("static") is not None,
            "isFinal":    m.group("final")  is not None,
            "returnType": return_type,
            "throws":     [t.strip() for t in throws_str.split(",") if t.strip()],
        })
    return methods


def extract_dependencies(content: str) -> list:
    skip = {
        "int", "long", "double", "float", "boolean",
        "String", "Integer", "Long", "Double", "Float", "Boolean",
        "List", "Map", "Set", "Optional",
    }
    deps = []
    for m in re.finditer(r"private\s+(?:final\s+)?([\w]+(?:<[^>]+>)?)\s+(\w+)\s*[;=]", content):
        t, n = m.group(1), m.group(2)
        if t not in skip and t.lower() not in {s.lower() for s in skip}:
            deps.append({"type": t, "name": n})
    return deps


if __name__ == "__main__":
    main()
