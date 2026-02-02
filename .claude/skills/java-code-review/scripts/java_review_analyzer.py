#!/usr/bin/env python3
"""
Java Code Review Analyzer

This script analyzes Java code for:
1. Runtime exception handling issues
2. Semantic code problems
3. Security vulnerabilities
"""

import sys
import re
import os
from typing import List, Dict, Tuple


class JavaReviewAnalyzer:
    def __init__(self):
        # Runtime exception patterns
        self.runtime_exception_patterns = [
            # Potential NullPointerException - look for .length() on possibly null strings
            r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\.\s*length\s*\(\s*\)',
            # Array access without bounds check
            r'\[[a-zA-Z_][a-zA-Z0-9_.\[\]]*\]',  # Array access patterns
            # parseInt without try-catch
            r'Integer\.parseInt\s*\(',
            r'Double\.parseDouble\s*\(',
            r'Float\.parseFloat\s*\(',
            r'Long\.parseLong\s*\(',
        ]

        # Security vulnerability patterns
        self.security_patterns = [
            # SQL injection - more comprehensive pattern
            r'[Ss][Ee][Ll][Ee][Cc][Tt]|[Ff][Rr][Oo][Mm]|[Ww][Hh][Ee][Rr][Ee]|[Uu][Pp][Dd][Aa][Tt][Ee]|[Dd][Ee][Ll][Ee][Tt][Ee]',
            r'(statement|query)\s*\+',
            r'execute\s*\(\s*[a-zA-Z_][a-zA-Z0-9_]*\s*\)',
            # Command injection
            r'Runtime\.getRuntime\s*\(\s*\)\.exec\s*\(',
            r'ProcessBuilder\s*\(',
            # Path traversal
            r'File\s*\(\s*[^\)]*request',
            # Hardcoded secrets - improved pattern
            r'password\s*=\s*"[^"]+"',
            r'hardcodedPassword\s*=\s*"[^"]+"',
            r'apiKey\s*=\s*"[^"]+"',
            r'secret\s*=\s*"[^"]+"',
        ]

        # Semantic issue patterns
        self.semantic_patterns = [
            # Equals without hashCode
            r'public boolean equals\s*\(\s*Object\s+',
            # Infinite loops
            r'while\s*\(\s*true\s*\)',
            # Unreachable code after return
            r'return\s+.+[\r\n].*[^{}]+',
            # Potential unused variables
            r'String\s+[a-zA-Z_][a-zA-Z0-9_]*\s*=',
        ]

    def analyze_file(self, file_path: str) -> Dict[str, List[Tuple[int, str, str]]]:
        """Analyze a Java file for potential issues."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.splitlines()
        results = {
            'runtime_exceptions': [],
            'security_vulnerabilities': [],
            'semantic_issues': []
        }

        # Check for runtime exception patterns
        for i, line in enumerate(lines, 1):
            for pattern in self.runtime_exception_patterns:
                if re.search(pattern, line):
                    results['runtime_exceptions'].append((i, line.strip(), "Potential runtime exception"))

        # Check for security vulnerability patterns
        for i, line in enumerate(lines, 1):
            for pattern in self.security_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    results['security_vulnerabilities'].append((i, line.strip(), "Potential security vulnerability"))

        # Check for semantic issues
        for i, line in enumerate(lines, 1):
            for pattern in self.semantic_patterns:
                if re.search(pattern, line):
                    results['semantic_issues'].append((i, line.strip(), "Potential semantic issue"))

        return results

    def analyze_code_snippet(self, code: str) -> Dict[str, List[Tuple[int, str, str]]]:
        """Analyze a Java code snippet for potential issues."""
        lines = code.splitlines()
        results = {
            'runtime_exceptions': [],
            'security_vulnerabilities': [],
            'semantic_issues': []
        }

        # Check for runtime exception patterns
        for i, line in enumerate(lines, 1):
            for pattern in self.runtime_exception_patterns:
                if re.search(pattern, line):
                    results['runtime_exceptions'].append((i, line.strip(), "Potential runtime exception"))

        # Check for security vulnerability patterns
        for i, line in enumerate(lines, 1):
            for pattern in self.security_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    results['security_vulnerabilities'].append((i, line.strip(), "Potential security vulnerability"))

        # Check for semantic issues
        for i, line in enumerate(lines, 1):
            for pattern in self.semantic_patterns:
                if re.search(pattern, line):
                    results['semantic_issues'].append((i, line.strip(), "Potential semantic issue"))

        return results

    def print_results(self, results: Dict[str, List[Tuple[int, str, str]]], file_path: str = None):
        """Print analysis results in a structured format."""
        print(f"\n{'='*60}")
        if file_path:
            print(f"ANALYSIS RESULTS FOR: {file_path}")
        else:
            print("ANALYSIS RESULTS FOR CODE SNIPPET")
        print(f"{'='*60}")

        categories = {
            'runtime_exceptions': 'RUNTIME EXCEPTION HANDLING ISSUES',
            'security_vulnerabilities': 'SECURITY VULNERABILITIES',
            'semantic_issues': 'SEMANTIC CODE ISSUES'
        }

        for category, title in categories.items():
            issues = results.get(category, [])
            if issues:
                print(f"\n{title}:")
                print("-" * len(title))
                for line_num, line_content, description in issues:
                    print(f"  Line {line_num}: {description}")
                    print(f"    Code: {line_content}")
            else:
                print(f"\n{title}: No issues detected")


def main():
    if len(sys.argv) < 2:
        print("Usage: python java_review_analyzer.py <java_file_or_directory>")
        print("Or pipe Java code directly: echo 'your java code' | python java_review_analyzer.py")
        sys.exit(1)

    analyzer = JavaReviewAnalyzer()

    # Prioritize file arguments over stdin when both are present
    target = sys.argv[1]

    # Check if target is a file or directory (and not just a code snippet)
    if os.path.exists(target):
        if os.path.isfile(target) and target.endswith('.java'):
            # Analyze single file
            results = analyzer.analyze_file(target)
            analyzer.print_results(results, target)
        elif os.path.isdir(target):
            # Analyze all Java files in directory
            for root, dirs, files in os.walk(target):
                for file in files:
                    if file.endswith('.java'):
                        file_path = os.path.join(root, file)
                        results = analyzer.analyze_file(file_path)
                        analyzer.print_results(results, file_path)
        else:
            # Analyze as code snippet passed as argument
            code_input = ' '.join(sys.argv[1:])
            results = analyzer.analyze_code_snippet(code_input)
            analyzer.print_results(results)
    else:
        # If target doesn't exist as file/directory, treat as code snippet
        code_input = ' '.join(sys.argv[1:])
        results = analyzer.analyze_code_snippet(code_input)
        analyzer.print_results(results)


if __name__ == "__main__":
    main()