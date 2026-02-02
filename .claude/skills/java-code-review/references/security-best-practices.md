# Java Security Best Practices Reference

## Input Validation

Always validate and sanitize user input before using it in your application:

```java
// Bad - Direct use of user input
String query = "SELECT * FROM users WHERE id = " + userInput;

// Good - Using parameterized queries
String query = "SELECT * FROM users WHERE id = ?";
PreparedStatement pstmt = connection.prepareStatement(query);
pstmt.setString(1, userInput);
```

## Exception Handling

Proper exception handling prevents information disclosure and application crashes:

```java
// Bad - Empty catch blocks
try {
    riskyOperation();
} catch (Exception e) {
    // Silent fail - bad practice
}

// Good - Proper logging and handling
try {
    riskyOperation();
} catch (SQLException e) {
    logger.error("Database error occurred", e);
    // Handle appropriately
} catch (Exception e) {
    logger.error("Unexpected error", e);
    throw new ServiceException("Operation failed", e);
}
```

## Resource Management

Always properly close resources to prevent leaks:

```java
// Bad - Resource leak potential
FileInputStream fis = new FileInputStream(file);
// Code that might throw exception
fis.close();

// Good - Try-with-resources
try (FileInputStream fis = new FileInputStream(file)) {
    // Process file
} catch (IOException e) {
    logger.error("Error processing file", e);
}
```

## Cryptography

Use strong cryptographic practices:

```java
// Bad - Weak encryption
Cipher cipher = Cipher.getInstance("DES");

// Good - Strong encryption
Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
```

## Authentication and Authorization

Always verify user permissions:

```java
// Bad - No authorization check
performAdminAction(userId);

// Good - Authorization check
if (hasPermission(user, "ADMIN")) {
    performAdminAction(userId);
} else {
    throw new UnauthorizedException("Insufficient privileges");
}
```

## Secure Random Generation

Use secure random generators:

```java
// Bad - Predictable random
Random rand = new Random(seed);

// Good - Secure random
SecureRandom secureRandom = new SecureRandom();