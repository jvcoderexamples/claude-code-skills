# Testing Private and Protected Members via Reflection

## When to Test Private Methods

| Test | Don't Test |
|------|------------|
| Complex private logic with edge cases | Simple private helpers |
| Private methods with business rules | Delegation-only methods |
| Security-sensitive private operations | Methods covered by public API tests |

**Principle**: Prefer testing through public API. Use reflection when private method has independent, valuable logic worth direct testing.

---

## Accessing Private Methods

### Basic Pattern

```java
@Test
void privateMethod_ShouldReturnExpected() throws Exception {
    // Get the private method
    Method method = TargetClass.class.getDeclaredMethod(
        "privateMethodName",
        String.class,    // Parameter types
        int.class
    );
    method.setAccessible(true);

    // Create instance
    TargetClass instance = new TargetClass();

    // Invoke
    Object result = method.invoke(instance, "arg1", 42);

    // Assert
    assertEquals(expectedValue, result);
}
```

### With No Parameters

```java
@Test
void privateNoArgMethod_ShouldWork() throws Exception {
    Method method = TargetClass.class.getDeclaredMethod("privateMethod");
    method.setAccessible(true);

    TargetClass instance = new TargetClass();
    String result = (String) method.invoke(instance);

    assertEquals("expected", result);
}
```

### With Primitive Parameters

```java
@Test
void privateMethodWithPrimitives_ShouldWork() throws Exception {
    // Use .class for primitives, not wrapper classes
    Method method = Calculator.class.getDeclaredMethod(
        "internalCalculate",
        int.class,      // NOT Integer.class
        double.class    // NOT Double.class
    );
    method.setAccessible(true);

    Calculator calc = new Calculator();
    double result = (double) method.invoke(calc, 5, 2.5);

    assertEquals(12.5, result, 0.001);
}
```

### With Object Parameters

```java
@Test
void privateMethodWithObjects_ShouldWork() throws Exception {
    Method method = Service.class.getDeclaredMethod(
        "processInternal",
        User.class,
        List.class
    );
    method.setAccessible(true);

    Service service = new Service();
    User user = new User("John");
    List<String> items = Arrays.asList("a", "b");

    Result result = (Result) method.invoke(service, user, items);

    assertNotNull(result);
}
```

### With Varargs

```java
@Test
void privateVarargsMethod_ShouldWork() throws Exception {
    // Varargs are arrays
    Method method = Formatter.class.getDeclaredMethod(
        "formatInternal",
        String.class,
        String[].class  // varargs as array
    );
    method.setAccessible(true);

    Formatter formatter = new Formatter();
    String[] args = {"a", "b", "c"};

    String result = (String) method.invoke(formatter, "pattern", args);

    assertNotNull(result);
}
```

---

## Accessing Private Fields

### Read Private Field

```java
@Test
void shouldReadPrivateField() throws Exception {
    TargetClass instance = new TargetClass();

    Field field = TargetClass.class.getDeclaredField("privateField");
    field.setAccessible(true);

    String value = (String) field.get(instance);

    assertEquals("expectedValue", value);
}
```

### Write Private Field

```java
@Test
void shouldSetPrivateField() throws Exception {
    TargetClass instance = new TargetClass();

    Field field = TargetClass.class.getDeclaredField("privateField");
    field.setAccessible(true);

    field.set(instance, "newValue");

    // Verify via getter or another read
    assertEquals("newValue", field.get(instance));
}
```

### Inject Mock into Private Field

```java
@Test
void shouldInjectMockIntoPrivateField() throws Exception {
    // Create instance without constructor injection
    Service service = new Service();

    // Create mock
    Repository mockRepo = mock(Repository.class);

    // Inject mock into private field
    Field repoField = Service.class.getDeclaredField("repository");
    repoField.setAccessible(true);
    repoField.set(service, mockRepo);

    // Setup mock behavior
    when(mockRepo.findById(1L)).thenReturn(Optional.of(new Entity()));

    // Test
    service.doSomething(1L);

    verify(mockRepo).findById(1L);
}
```

---

## Testing Private Static Methods

```java
@Test
void privateStaticMethod_ShouldWork() throws Exception {
    Method method = Utility.class.getDeclaredMethod(
        "privateStaticMethod",
        String.class
    );
    method.setAccessible(true);

    // Pass null as first argument for static methods
    String result = (String) method.invoke(null, "input");

    assertEquals("expected", result);
}
```

---

## Exception Handling in Reflection

### Catching Exceptions from Private Methods

```java
@Test
void privateMethod_ShouldThrowException() throws Exception {
    Method method = Validator.class.getDeclaredMethod(
        "validateInternal",
        String.class
    );
    method.setAccessible(true);

    Validator validator = new Validator();

    // InvocationTargetException wraps the actual exception
    InvocationTargetException thrown = assertThrows(
        InvocationTargetException.class,
        () -> method.invoke(validator, "invalid")
    );

    // Unwrap to get actual exception
    Throwable actual = thrown.getCause();
    assertTrue(actual instanceof IllegalArgumentException);
    assertEquals("Invalid input", actual.getMessage());
}
```

### Alternative with Try-Catch

```java
@Test
void privateMethod_ShouldThrowExpectedException() throws Exception {
    Method method = Service.class.getDeclaredMethod("riskyOperation");
    method.setAccessible(true);

    Service service = new Service();

    try {
        method.invoke(service);
        fail("Expected exception was not thrown");
    } catch (InvocationTargetException e) {
        assertTrue(e.getCause() instanceof CustomException);
    }
}
```

---

## Utility Helper Class

Create a test utility for cleaner reflection tests:

```java
public class ReflectionTestUtils {

    public static Object invokePrivateMethod(
            Object target,
            String methodName,
            Class<?>[] paramTypes,
            Object... args) throws Exception {

        Method method = target.getClass().getDeclaredMethod(methodName, paramTypes);
        method.setAccessible(true);
        return method.invoke(target, args);
    }

    public static Object invokePrivateMethod(
            Object target,
            String methodName) throws Exception {

        Method method = target.getClass().getDeclaredMethod(methodName);
        method.setAccessible(true);
        return method.invoke(target);
    }

    public static <T> T getPrivateField(
            Object target,
            String fieldName,
            Class<T> fieldType) throws Exception {

        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        return fieldType.cast(field.get(target));
    }

    public static void setPrivateField(
            Object target,
            String fieldName,
            Object value) throws Exception {

        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(target, value);
    }

    public static Object invokePrivateStaticMethod(
            Class<?> targetClass,
            String methodName,
            Class<?>[] paramTypes,
            Object... args) throws Exception {

        Method method = targetClass.getDeclaredMethod(methodName, paramTypes);
        method.setAccessible(true);
        return method.invoke(null, args);
    }
}
```

### Using the Utility

```java
@Test
void shouldUseReflectionUtils() throws Exception {
    MyService service = new MyService();

    // Invoke private method with params
    String result = (String) ReflectionTestUtils.invokePrivateMethod(
        service,
        "processInternal",
        new Class<?>[] { String.class, int.class },
        "input", 42
    );

    assertEquals("expected", result);
}
```

---

## Spring's ReflectionTestUtils

If using Spring, leverage built-in utilities:

```java
import org.springframework.test.util.ReflectionTestUtils;

@Test
void shouldUseSpringReflectionUtils() {
    MyService service = new MyService();

    // Set private field
    ReflectionTestUtils.setField(service, "privateField", "value");

    // Get private field
    String value = (String) ReflectionTestUtils.getField(service, "privateField");

    // Invoke private method
    String result = ReflectionTestUtils.invokeMethod(
        service,
        "privateMethod",
        "arg1", 42
    );
}
```

---

## Testing Private Constructors

```java
@Test
void privateConstructor_ShouldWork() throws Exception {
    // Get private constructor
    Constructor<Singleton> constructor =
        Singleton.class.getDeclaredConstructor();
    constructor.setAccessible(true);

    // Create instance
    Singleton instance = constructor.newInstance();

    assertNotNull(instance);
}
```

---

## Testing Inner/Nested Classes

```java
@Test
void privateInnerClass_ShouldBeTestable() throws Exception {
    // Access private inner class
    Class<?> innerClass = Class.forName("OuterClass$PrivateInner");

    // Get constructor (inner class has implicit outer reference)
    Constructor<?> constructor = innerClass.getDeclaredConstructor(OuterClass.class);
    constructor.setAccessible(true);

    // Create instances
    OuterClass outer = new OuterClass();
    Object inner = constructor.newInstance(outer);

    // Access methods on inner class
    Method method = innerClass.getDeclaredMethod("innerMethod");
    method.setAccessible(true);

    Object result = method.invoke(inner);
    assertNotNull(result);
}
```

---

## Best Practices

| Do | Don't |
|----|-------|
| Test through public API first | Reflexively test every private method |
| Use reflection for complex private logic | Use reflection for simple getters/setters |
| Create utility methods for repeated patterns | Duplicate reflection code everywhere |
| Handle InvocationTargetException properly | Ignore wrapped exceptions |
| Document why private testing is needed | Leave unexplained reflection tests |
