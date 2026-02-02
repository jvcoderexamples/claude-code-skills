#!/bin/bash
# Validation script for the Java Code Review skill

echo "Validating Java Code Review skill..."

# Check if required files exist
REQUIRED_FILES=(
    ".claude/skills/java-code-review/SKILL.md"
    ".claude/skills/java-code-review/scripts/java_review_analyzer.py"
    ".claude/skills/java-code-review/scripts/review-java-code.sh"
    ".claude/skills/java-code-review/references/security-best-practices.md"
    ".claude/skills/java-code-review/references/runtime-exceptions.md"
    ".claude/skills/java-code-review/references/semantic-issues.md"
)

MISSING_FILES=()
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -eq 0 ]; then
    echo "✓ All required files are present"
else
    echo "✗ Missing files:"
    printf '%s\n' "${MISSING_FILES[@]}"
    exit 1
fi

# Check if scripts are executable
if [ -x ".claude/skills/java-code-review/scripts/review-java-code.sh" ]; then
    echo "✓ Review script is executable"
else
    echo "✗ Review script is not executable"
    exit 1
fi

if [ -x ".claude/skills/java-code-review/scripts/java_review_analyzer.py" ]; then
    echo "✓ Analyzer script is executable"
else
    echo "✗ Analyzer script is not executable"
    exit 1
fi

# Test that the skill has proper YAML frontmatter
FRONTMATTER_CHECK=$(head -n 10 ".claude/skills/java-code-review/SKILL.md" | grep -E "^---$" | wc -l)
if [ "$FRONTMATTER_CHECK" -ge 2 ]; then
    echo "✓ SKILL.md has proper YAML frontmatter"
else
    echo "✗ SKILL.md is missing proper YAML frontmatter"
    exit 1
fi

echo ""
echo "Java Code Review skill validation completed successfully!"
echo ""
echo "The skill provides:"
echo "- Runtime exception handling analysis"
echo "- Semantic code checks"
echo "- Security vulnerability assessment"
echo "- Automated analysis scripts"
echo "- Detailed reference documentation"