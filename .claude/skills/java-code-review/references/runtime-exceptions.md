# Java Runtime Exception Patterns Reference

## Common Exception Types

### NullPointerException (NPE)
Most common Java exception, occurs when calling methods on null objects:

```java
// Common NPE patterns
String str = null;
int len = str.length(); // NPE

List<String> list = null;
list.add("item"); // NPE

String[] arr = null;
int size = arr.length; // NPE
```

### Prevention Strategies
```java
// Defensive programming
if (obj != null && obj.getProperty() != null) {
    obj.getProperty().doSomething();
}

// Use Optional (Java 8+)
Optional<String> opt = Optional.ofNullable(getString());
opt.ifPresent(s -> s.length());

// Initialize collections properly
List<String> list = new ArrayList<>(); // Instead of null
```

## Array Exceptions

### ArrayIndexOutOfBoundsException
```java
// Risky patterns
int[] arr = new int[5];
int val = arr[10]; // AIOOBE

String[] items = getItems();
for (int i = 0; i <= items.length; i++) { // Off-by-one error
    System.out.println(items[i]);
}
```

### Prevention
```java
// Safe array access
if (index >= 0 && index < arr.length) {
    val = arr[index];
}

// Safe loop
for (int i = 0; i < items.length; i++) { // Use < not <=
    System.out.println(items[i]);
}
```

## Number Format Exceptions

### NumberFormatException
```java
// Risky parsing
int num = Integer.parseInt(userInput); // May throw NFE
double d = Double.parseDouble(nullableValue); // May throw NFE
```

### Safe Parsing
```java
// Safe integer parsing
public static Optional<Integer> safeParseInt(String str) {
    try {
        return Optional.of(Integer.parseInt(str));
    } catch (NumberFormatException e) {
        return Optional.empty();
    }
}

// Or use Apache Commons (if available)
if (StringUtils.isNumeric(str)) {
    int num = Integer.parseInt(str);
}
```

## Concurrent Modification

### ConcurrentModificationException
```java
// Dangerous iteration
List<String> list = new ArrayList<>();
list.add("a");
list.add("b");

for (String s : list) {
    if (condition) {
        list.remove(s); // CME
    }
}
```

### Safe Modification
```java
// Safe iteration and removal
Iterator<String> iter = list.iterator();
while (iter.hasNext()) {
    String s = iter.next();
    if (condition) {
        iter.remove(); // Safe
    }
}

// Or use streams
list.removeIf(item -> condition);
```

## Resource Leaks

### IOException and Resource Management
```java
// Risky resource handling
FileInputStream fis = new FileInputStream(file);
BufferedReader reader = new BufferedReader(new InputStreamReader(fis));
String line = reader.readLine(); // May throw IOException
// Resource may not be closed if exception occurs

// Safe resource handling
try (FileInputStream fis = new FileInputStream(file);
     BufferedReader reader = new BufferedReader(new InputStreamReader(fis))) {
    String line = reader.readLine();
    // Resources automatically closed
} catch (IOException e) {
    // Handle exception
}
```

## Exception Propagation Best Practices

### Checked vs Unchecked Exceptions
```java
// Proper exception wrapping
public void processData(String data) throws ValidationException {
    try {
        // Some processing that may throw IOException
        riskyOperation(data);
    } catch (IOException e) {
        throw new ValidationException("Invalid data format", e);
    }
}

// Don't ignore exceptions
try {
    operation();
} catch (Exception e) {
    // At minimum log the exception
    logger.warn("Expected occasional error", e);
}
```