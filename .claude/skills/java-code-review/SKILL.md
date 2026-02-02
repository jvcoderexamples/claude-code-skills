---
name: java-code-review
description: Comprehensive Java code review skill that analyzes code for runtime exception handling, semantic correctness, and security vulnerabilities. Use when reviewing Java code to identify potential runtime exceptions, semantic code issues, and security vulnerabilities that could impact application stability, correctness, and security posture.
---

# Java Code Review

## Overview

This skill enables comprehensive analysis of Java code to identify potential runtime exceptions, semantic code issues, and security vulnerabilities. It provides structured feedback to improve code quality, maintainability, and security.

## Core Capabilities

### 1. Runtime Exception Handling Analysis
Reviews code to identify potential runtime exceptions and improper exception handling patterns:
- Unhandled checked and unchecked exceptions
- Improper exception propagation
- Empty catch blocks
- Resource leaks in try-catch blocks
- Improper use of finally blocks

### 2. Semantic Code Checks
Analyzes code for semantic correctness and best practices:
- Logic errors and incorrect control flow
- Incorrect use of Java APIs
- Performance anti-patterns
- Memory leaks
- Concurrency issues
- Null pointer exceptions
- Type safety violations

### 3. Security Vulnerability Assessment
Identifies potential security vulnerabilities in Java code:
- SQL injection vulnerabilities
- Cross-site scripting (XSS) risks
- Command injection possibilities
- Insecure deserialization
- Hardcoded secrets
- Weak cryptographic implementations
- Path traversal vulnerabilities
- Insecure random number generation

## Quick Start

To use this skill for Java code review:

1. **Prepare code for review**: Organize Java files or code snippets for analysis
2. **Specify review focus**: Indicate if you want comprehensive review or specific aspects (runtime exceptions, semantic checks, or security vulnerabilities)
3. **Run analysis**: Use the review scripts or manual analysis based on the guidance below
4. **Review findings**: Examine the output for issues and recommendations

## Runtime Exception Handling Analysis

### When to Use
Use when reviewing Java code to identify potential runtime crashes, exception handling issues, or resource management problems.

### Analysis Checklist
- Look for unhandled NullPointerExceptions
- Check for ArrayIndexOutOfBoundsException risks
- Verify proper handling of ClassCastException
- Identify potential NumberFormatException in parsing
- Review resource management in try-catch-finally blocks
- Check for proper exception chaining
- Ensure exceptions are logged appropriately

### Common Patterns to Check
```java
// Problematic pattern - potential NPE
String value = obj.getString();
int length = value.length(); // Could throw NPE if getString() returns null

// Better approach
String value = obj.getString();
if (value != null) {
    int length = value.length();
}

// Problematic pattern - resource leak risk
FileInputStream fis = new FileInputStream(file);
// Missing try-finally or try-with-resources
```

## Semantic Code Checks

### When to Use
Use when evaluating code correctness, performance, and adherence to Java best practices.

### Analysis Checklist
- Verify logical correctness of algorithms
- Check for infinite loops or unreachable code
- Identify inefficient operations
- Review thread safety in concurrent code
- Check for proper equals/hashCode contracts
- Validate generic type usage
- Review memory usage patterns

### Common Issues to Detect
- Loop termination conditions that may cause infinite loops
- Object comparison using == instead of equals()
- Improper synchronization in multithreaded code
- Collection misuse leading to performance issues
- Misuse of immutable objects causing unexpected behavior

## Security Vulnerability Assessment

### When to Use
Use when evaluating code for security risks that could compromise the application or its data.

### Analysis Checklist
- Input validation for all external data
- Sanitization of user inputs before using in queries/command execution
- Proper handling of sensitive data
- Secure configuration practices
- Proper authentication and authorization checks
- Safe use of reflection and dynamic code execution

### Security Patterns to Watch For
```java
// SQL Injection vulnerability
String query = "SELECT * FROM users WHERE id = " + userInput;
Statement stmt = connection.createStatement();
ResultSet rs = stmt.executeQuery(query);

// Safer approach
String query = "SELECT * FROM users WHERE id = ?";
PreparedStatement pstmt = connection.prepareStatement(query);
pstmt.setString(1, userInput);
```

## Analysis Workflow

1. **Initial Scan**: Perform a quick scan for obvious issues in each category
2. **Detailed Analysis**: Dive deeper into specific areas based on code complexity
3. **Context Evaluation**: Consider the broader application context for impact assessment
4. **Recommendation Generation**: Provide specific, actionable recommendations
5. **Priority Ranking**: Rank issues by severity (Critical, High, Medium, Low)

## Analysis Workflow

1. **Initial Scan**: Perform a quick scan for obvious issues in each category
2. **Detailed Analysis**: Dive deeper into specific areas based on code complexity
3. **Context Evaluation**: Consider the broader application context for impact assessment
4. **Recommendation Generation**: Provide specific, actionable recommendations
5. **Priority Ranking**: Rank issues by severity (Critical, High, Medium, Low)

## Severity Classification

- **Critical**: Issues that could lead to application crash, data corruption, or security breach
- **High**: Issues that could cause significant functional problems or performance degradation
- **Medium**: Issues that affect maintainability, readability, or minor functionality
- **Low**: Minor stylistic or best-practice deviations

## Usage Examples

### Using the Analysis Script

```bash
# Analyze a single Java file
bash scripts/review-java-code.sh MyJavaFile.java

# Analyze all Java files in a directory
bash scripts/review-java-code.sh -t security /path/to/java/project/src

# Focus on runtime exception handling
bash scripts/review-java-code.sh -t runtime ./src/main/java/com/example/
```

### Manual Analysis

When performing manual code review:

1. **For Runtime Exceptions**: Look for potential null pointer accesses, array bounds issues, and improper exception handling
2. **For Security Issues**: Check for input validation, SQL injection, command injection, and hardcoded secrets
3. **For Semantic Issues**: Verify logic correctness, proper equals/hashCode implementation, and concurrency safety
