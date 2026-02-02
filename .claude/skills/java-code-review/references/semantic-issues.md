# Java Semantic Code Issues Reference

## Logic Errors

### Infinite Loops
```java
// Common infinite loop patterns
for (int i = 0; i < 10; i--) { // i-- instead of i++
    // This will loop infinitely or until integer overflow
}

while (true) { // Unless there's a break condition
    // Potentially infinite
}

int i = 0;
while (i < 10) {
    processItem(i);
    // Forgot to increment i - infinite loop
}
```

### Unreachable Code
```java
// Code after return statement
public int getValue() {
    return 42;
    System.out.println("This will never execute"); // Unreachable
}

// Break/continue in wrong place
for (int i = 0; i < 10; i++) {
    if (condition) {
        break;
    }
    process(i);
    break; // This makes the loop execute at most once
}
```

## Object-Oriented Programming Issues

### equals() and hashCode() Contract
```java
// Violation of equals/hashCode contract
public class Person {
    private String name;
    private int age;

    @Override
    public boolean equals(Object obj) {
        // Implementation of equals
    }
    // Missing hashCode() - violates contract
}
```

### Proper Implementation
```java
public class Person {
    private String name;
    private int age;

    @Override
    public boolean equals(Object obj) {
        if (this == obj) return true;
        if (obj == null || getClass() != obj.getClass()) return false;
        Person person = (Person) obj;
        return age == person.age && Objects.equals(name, person.name);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, age);
    }
}
```

## Performance Anti-patterns

### Inefficient String Concatenation
```java
// Inefficient
String result = "";
for (String item : items) {
    result += item; // Creates many intermediate String objects
}

// Efficient
StringBuilder sb = new StringBuilder();
for (String item : items) {
    sb.append(item);
}
String result = sb.toString();
```

### Boxed Primitives Misuse
```java
// Inefficient autoboxing in loops
List<Integer> list = new ArrayList<>();
for (int i = 0; i < 1000000; i++) {
    list.add(i); // Autoboxing from int to Integer
}

// Better for primitive operations
IntStream.range(0, 1000000)
         .boxed()
         .collect(Collectors.toList());
```

## Concurrency Issues

### Race Conditions
```java
// Non-thread-safe counter
public class Counter {
    private int count = 0;

    public void increment() {
        count++; // Not atomic - race condition possible
    }
}

// Thread-safe version
public class Counter {
    private int count = 0;

    public synchronized void increment() {
        count++;
    }
}

// Or using atomic operations
public class Counter {
    private AtomicInteger count = new AtomicInteger(0);

    public void increment() {
        count.incrementAndGet();
    }
}
```

### Deadlock
```java
// Potential deadlock situation
public class DeadlockExample {
    private final Object lock1 = new Object();
    private final Object lock2 = new Object();

    public void method1() {
        synchronized(lock1) {
            synchronized(lock2) {
                // Do something
            }
        }
    }

    public void method2() {
        synchronized(lock2) {
            synchronized(lock1) {
                // Do something
            }
        }
    }
}
```

## Memory Issues

### Memory Leaks
```java
// Static collection holding references
public class MemoryLeakExample {
    private static List<Object> cache = new ArrayList<>();

    public void addToCache(Object obj) {
        cache.add(obj); // Objects never removed - memory leak
    }
}

// Inner class holding reference to outer class
public class OuterClass {
    private Object data = new Object();

    // Non-static inner class holds reference to outer instance
    class InnerClass {
        // Inner class implementation
    }
}
```

### Proper Collection Usage
```java
// Using the wrong collection type
List<Integer> numbers = new ArrayList<>();
// If doing lots of insertions/removals in middle, use LinkedList
List<Integer> numbers = new LinkedList<>();

// Inefficient iteration over HashMap
Map<String, Object> map = new HashMap<>();
for (String key : map.keySet()) {
    Object value = map.get(key); // Two lookups
}

// More efficient
for (Map.Entry<String, Object> entry : map.entrySet()) {
    String key = entry.getKey();
    Object value = entry.getValue(); // One iteration, one lookup
}
```

## Generic Type Issues

### Raw Types
```java
// Raw type usage - not type-safe
List list = new ArrayList(); // Should specify type parameter
list.add("string");
list.add(123); // Compiler won't catch type mismatch

// Proper generic usage
List<String> list = new ArrayList<>();
list.add("string");
// list.add(123); // Compiler error - type safe
```

### Wildcard Usage
```java
// Inappropriate wildcard usage
public void processList(List<?> list) {
    // Can't add elements (except null) to List<?>
    list.add("item"); // Compile error
}

// Better - use bounded wildcards when needed
public void processNumbers(List<? extends Number> numbers) {
    for (Number num : numbers) {
        System.out.println(num.doubleValue());
    }
}
```

## Null Handling

### Improper Null Checks
```java
// Inconsistent null handling
public String process(String input) {
    if (input.length() > 0) { // NPE if input is null
        return input.toUpperCase();
    }
    return null;
}

// Better null handling
public String process(String input) {
    if (input != null && input.length() > 0) {
        return input.toUpperCase();
    }
    return null;
}

// Or use Optional
public Optional<String> process(String input) {
    return Optional.ofNullable(input)
                   .filter(s -> s.length() > 0)
                   .map(String::toUpperCase);
}
```

## Method Design Issues

### Violating Liskov Substitution Principle
```java
// Subclass changing method contract
class Rectangle {
    protected int width, height;

    public void setWidth(int width) { this.width = width; }
    public void setHeight(int height) { this.height = height; }
    public int getArea() { return width * height; }
}

class Square extends Rectangle {
    @Override
    public void setWidth(int width) {
        this.width = width;
        this.height = width; // Changes behavior - violates LSP
    }
}
```