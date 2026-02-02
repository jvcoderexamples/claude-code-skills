#!/bin/bash
# Java Code Review Script
# Analyzes Java code for runtime exceptions, semantic issues, and security vulnerabilities

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    echo "Usage: $0 [OPTIONS] <java_file_or_directory>"
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -t, --type     Specify review type: all, runtime, semantic, security (default: all)"
    echo ""
    echo "Examples:"
    echo "  $0 MyJavaFile.java"
    echo "  $0 -t security /path/to/java/project"
    echo "  $0 -t runtime ./src/main/java/com/example/"
}

REVIEW_TYPE="all"

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -t|--type)
            REVIEW_TYPE="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            JAVA_TARGET="$1"
            shift
            ;;
    esac
done

if [ -z "$JAVA_TARGET" ]; then
    echo "Error: Java file or directory not specified"
    usage
    exit 1
fi

if [ ! -e "$JAVA_TARGET" ]; then
    echo "Error: File or directory does not exist: $JAVA_TARGET"
    exit 1
fi

echo "Starting Java code review for: $JAVA_TARGET"
echo "Review type: $REVIEW_TYPE"
echo ""

# Run the Python analyzer
python3 "$SCRIPT_DIR/java_review_analyzer.py" "$JAVA_TARGET"

echo ""
echo "Review completed. For more detailed information, refer to the reference documents:"
echo "- Security best practices: references/security-best-practices.md"
echo "- Runtime exceptions: references/runtime-exceptions.md"
echo "- Semantic issues: references/semantic-issues.md"