#!/usr/bin/env python3
"""
Scan Maven Java project source folder and identify classes needing unit tests.
Outputs JSON with class information for test generation.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set

TRACKING_FILE = ".junit-generator-tracking.json"


def check_maven_project(project_root: str) -> bool:
    """Check if project is a Maven project."""
    pom_path = Path(project_root) / "pom.xml"
    return pom_path.exists()


def check_maven_dependencies(project_root: str) -> Dict:
    """Check if pom.xml has required test dependencies."""
    pom_path = Path(project_root) / "pom.xml"
    if not pom_path.exists():
        return {"hasPom": False}

    with open(pom_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return {
        "hasPom": True,
        "hasJunit5": "junit-jupiter" in content,
        "hasMockito": "mockito-core" in content or "mockito-junit-jupiter" in content,
        "hasSurefire": "maven-surefire-plugin" in content
    }


def load_tracking(project_root: str) -> Dict:
    """Load existing tracking data."""
    tracking_path = Path(project_root) / TRACKING_FILE
    if tracking_path.exists():
        with open(tracking_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "generated": [],
        "pending": [],
        "failed": {},
        "lastRun": None,
        "projectRoot": project_root
    }


def save_tracking(project_root: str, tracking: Dict) -> None:
    """Save tracking data."""
    tracking_path = Path(project_root) / TRACKING_FILE
    tracking["lastRun"] = datetime.now().isoformat()
    with open(tracking_path, 'w', encoding='utf-8') as f:
        json.dump(tracking, f, indent=2)


def extract_class_info(file_path: Path) -> Optional[Dict]:
    """Extract class information from Java file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return None

    # Extract package
    package_match = re.search(r'package\s+([\w.]+)\s*;', content)
    package = package_match.group(1) if package_match else ""

    # Extract class name (handle class, interface, enum, record)
    class_match = re.search(
        r'(?:public\s+)?(?:abstract\s+)?(?:final\s+)?'
        r'(?:class|interface|enum|record)\s+(\w+)',
        content
    )
    if not class_match:
        return None

    class_name = class_match.group(1)
    full_class_name = f"{package}.{class_name}" if package else class_name

    # Determine class type
    class_type = "class"
    if re.search(r'\binterface\s+' + class_name, content):
        class_type = "interface"
    elif re.search(r'\benum\s+' + class_name, content):
        class_type = "enum"
    elif re.search(r'\brecord\s+' + class_name, content):
        class_type = "record"
    elif re.search(r'\babstract\s+class\s+' + class_name, content):
        class_type = "abstract"

    # Extract methods
    methods = extract_methods(content)

    # Extract dependencies (fields with type annotations or constructor params)
    dependencies = extract_dependencies(content)

    return {
        "filePath": str(file_path),
        "package": package,
        "className": class_name,
        "fullClassName": full_class_name,
        "classType": class_type,
        "methods": methods,
        "dependencies": dependencies,
        "hasStaticMethods": any(m.get("isStatic") for m in methods),
        "hasPrivateMethods": any(m.get("visibility") == "private" for m in methods)
    }


def extract_methods(content: str) -> List[Dict]:
    """Extract method signatures from Java content."""
    methods = []

    # Pattern for method declarations
    method_pattern = re.compile(
        r'(?P<visibility>public|private|protected)?\s*'
        r'(?P<static>static)?\s*'
        r'(?P<final>final)?\s*'
        r'(?P<returnType>[\w<>,\s\[\]]+)\s+'
        r'(?P<name>\w+)\s*'
        r'\((?P<params>[^)]*)\)\s*'
        r'(?:throws\s+(?P<throws>[\w,\s]+))?\s*\{',
        re.MULTILINE
    )

    for match in method_pattern.finditer(content):
        # Skip constructors (return type same as method name typically doesn't happen)
        method_name = match.group('name')
        return_type = match.group('returnType').strip()

        # Skip if it looks like a constructor
        if return_type == method_name:
            continue

        methods.append({
            "name": method_name,
            "visibility": match.group('visibility') or "package-private",
            "isStatic": bool(match.group('static')),
            "isFinal": bool(match.group('final')),
            "returnType": return_type,
            "parameters": parse_parameters(match.group('params')),
            "throws": [t.strip() for t in (match.group('throws') or "").split(",") if t.strip()]
        })

    return methods


def parse_parameters(params_str: str) -> List[Dict]:
    """Parse method parameters."""
    if not params_str.strip():
        return []

    params = []
    # Simple parsing - split by comma but handle generics
    depth = 0
    current = ""

    for char in params_str:
        if char in '<':
            depth += 1
        elif char in '>':
            depth -= 1
        elif char == ',' and depth == 0:
            if current.strip():
                params.append(parse_single_param(current.strip()))
            current = ""
            continue
        current += char

    if current.strip():
        params.append(parse_single_param(current.strip()))

    return params


def parse_single_param(param: str) -> Dict:
    """Parse a single parameter."""
    parts = param.split()
    if len(parts) >= 2:
        # Handle annotations
        annotations = [p for p in parts[:-2] if p.startswith('@')]
        type_name = parts[-2]
        param_name = parts[-1]
        return {"type": type_name, "name": param_name, "annotations": annotations}
    elif len(parts) == 2:
        return {"type": parts[0], "name": parts[1], "annotations": []}
    return {"type": param, "name": "unknown", "annotations": []}


def extract_dependencies(content: str) -> List[Dict]:
    """Extract class dependencies from fields and constructor."""
    dependencies = []

    # Field injection patterns (@Autowired, @Inject, etc.)
    field_pattern = re.compile(
        r'(?:@(?:Autowired|Inject|Mock|InjectMocks|Resource)\s+)?'
        r'private\s+(?:final\s+)?(\w+(?:<[^>]+>)?)\s+(\w+)\s*[;=]'
    )

    for match in field_pattern.finditer(content):
        dep_type = match.group(1)
        dep_name = match.group(2)

        # Skip primitive types and common Java types
        if dep_type.lower() in ['int', 'long', 'double', 'float', 'boolean',
                                 'string', 'integer', 'list', 'map', 'set']:
            continue

        dependencies.append({
            "type": dep_type,
            "name": dep_name
        })

    return dependencies


def find_java_files(source_folder: str, exclusions: List[str] = None) -> List[Path]:
    """Find all Java files in source folder."""
    source_path = Path(source_folder)
    if not source_path.exists():
        print(f"Error: Source folder does not exist: {source_folder}", file=sys.stderr)
        sys.exit(1)

    exclusions = exclusions or []
    java_files = []

    for java_file in source_path.rglob("*.java"):
        # Check exclusions
        relative_path = str(java_file.relative_to(source_path))
        skip = False

        for pattern in exclusions:
            if pattern in relative_path:
                skip = True
                break

        if not skip:
            java_files.append(java_file)

    return java_files


def check_existing_test(class_info: Dict, test_folder: str) -> bool:
    """Check if test already exists for a class."""
    if not test_folder:
        return False

    test_path = Path(test_folder)
    package_path = class_info["package"].replace(".", os.sep)
    test_file = test_path / package_path / f"{class_info['className']}Test.java"

    return test_file.exists()


def scan_project(
    source_folder: str,
    test_folder: str = None,
    exclusions: List[str] = None,
    project_root: str = None
) -> Dict:
    """Scan Maven project and return analysis results."""

    project_root = project_root or str(Path(source_folder).parent.parent)

    # Check Maven project
    if not check_maven_project(project_root):
        return {
            "status": "error",
            "message": f"No pom.xml found at {project_root}. This skill requires a Maven project."
        }

    # Check Maven dependencies
    deps = check_maven_dependencies(project_root)

    tracking = load_tracking(project_root)
    tracking["mavenDependencies"] = deps

    # Find Java files
    java_files = find_java_files(source_folder, exclusions)

    # Analyze each file
    classes = []
    for java_file in java_files:
        class_info = extract_class_info(java_file)
        if class_info:
            # Skip interfaces (usually no tests needed)
            if class_info["classType"] == "interface":
                continue

            # Check if already generated
            if class_info["fullClassName"] in tracking["generated"]:
                class_info["status"] = "generated"
            elif check_existing_test(class_info, test_folder):
                class_info["status"] = "existing"
                tracking["generated"].append(class_info["fullClassName"])
            elif class_info["fullClassName"] in tracking.get("failed", {}):
                class_info["status"] = "failed"
                class_info["failureReason"] = tracking["failed"][class_info["fullClassName"]]
            else:
                class_info["status"] = "pending"

            classes.append(class_info)

    # Update pending list
    pending = [c["fullClassName"] for c in classes if c["status"] == "pending"]
    tracking["pending"] = pending

    # Save tracking
    save_tracking(project_root, tracking)

    # Summary
    summary = {
        "totalClasses": len(classes),
        "pending": len([c for c in classes if c["status"] == "pending"]),
        "generated": len([c for c in classes if c["status"] in ["generated", "existing"]]),
        "failed": len([c for c in classes if c["status"] == "failed"]),
        "withStaticMethods": len([c for c in classes if c.get("hasStaticMethods")]),
        "withPrivateMethods": len([c for c in classes if c.get("hasPrivateMethods")])
    }

    return {
        "buildTool": "maven",
        "mavenDependencies": deps,
        "summary": summary,
        "classes": classes,
        "tracking": tracking
    }


def main():
    parser = argparse.ArgumentParser(
        description="Scan Maven Java project for test generation"
    )
    parser.add_argument(
        "source_folder",
        nargs="?",
        default="src/main/java",
        help="Path to Java source folder (default: src/main/java)"
    )
    parser.add_argument(
        "--test-folder",
        default="src/test/java",
        help="Path to test folder (default: src/test/java)"
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Patterns to exclude (can be repeated)"
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root directory containing pom.xml (default: current directory)"
    )
    parser.add_argument(
        "--output",
        choices=["json", "summary", "pending"],
        default="summary",
        help="Output format"
    )

    args = parser.parse_args()

    results = scan_project(
        source_folder=args.source_folder,
        test_folder=args.test_folder,
        exclusions=args.exclude,
        project_root=args.project_root
    )

    # Handle error case
    if results.get("status") == "error":
        print(f"Error: {results.get('message')}")
        sys.exit(1)

    if args.output == "json":
        print(json.dumps(results, indent=2))
    elif args.output == "pending":
        # Output only pending classes for processing
        pending = [c for c in results["classes"] if c["status"] == "pending"]
        print(json.dumps(pending, indent=2))
    else:
        # Summary output
        s = results["summary"]
        deps = results["tracking"].get("mavenDependencies", {})

        print(f"\n=== Maven Project Scan Results ===")
        print(f"Project root: {args.project_root}")
        print(f"Source folder: {args.source_folder}")

        # Maven dependencies status
        print(f"\nMaven Dependencies:")
        print(f"  JUnit 5:  {'✓' if deps.get('hasJunit5') else '✗ (add junit-jupiter to pom.xml)'}")
        print(f"  Mockito:  {'✓' if deps.get('hasMockito') else '✗ (add mockito-core to pom.xml)'}")
        print(f"  Surefire: {'✓' if deps.get('hasSurefire') else '✗ (add maven-surefire-plugin)'}")

        print(f"\nClasses Found: {s['totalClasses']}")
        print(f"  Pending:   {s['pending']}")
        print(f"  Generated: {s['generated']}")
        print(f"  Failed:    {s['failed']}")
        print(f"\nClasses with static methods:  {s['withStaticMethods']}")
        print(f"Classes with private methods: {s['withPrivateMethods']}")

        if s['pending'] > 0:
            print(f"\nRun with --output pending to get list of classes needing tests")


if __name__ == "__main__":
    main()
