# JUnit 5 Patterns Reference

## Essential Imports

```java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Disabled;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.MethodSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;

import static org.junit.jupiter.api.Assertions.*;
```

---

## Test Structure

### Basic Test Class

```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private UserService underTest;

    @BeforeEach
    void setUp() {
        // Reset state before each test
    }

    @Test
    @DisplayName("findById should return user when exists")
    void findById_ShouldReturnUser_WhenUserExists() {
        // Arrange
        User expected = new User(1L, "John");
        when(userRepository.findById(1L)).thenReturn(Optional.of(expected));

        // Act
        User result = underTest.findById(1L);

        // Assert
        assertNotNull(result);
        assertEquals("John", result.getName());
    }
}
```

### Nested Test Classes

```java
class CalculatorTest {

    private Calculator calculator;

    @BeforeEach
    void setUp() {
        calculator = new Calculator();
    }

    @Nested
    @DisplayName("Addition tests")
    class AdditionTests {

        @Test
        void shouldAddPositiveNumbers() {
            assertEquals(5, calculator.add(2, 3));
        }

        @Test
        void shouldAddNegativeNumbers() {
            assertEquals(-5, calculator.add(-2, -3));
        }
    }

    @Nested
    @DisplayName("Division tests")
    class DivisionTests {

        @Test
        void shouldDivideNumbers() {
            assertEquals(2, calculator.divide(6, 3));
        }

        @Test
        void shouldThrowOnDivisionByZero() {
            assertThrows(ArithmeticException.class,
                () -> calculator.divide(6, 0));
        }
    }
}
```

---

## Assertions

### Basic Assertions

```java
// Equality
assertEquals(expected, actual);
assertEquals(expected, actual, "Custom message");
assertNotEquals(unexpected, actual);

// Null checks
assertNull(object);
assertNotNull(object);

// Boolean
assertTrue(condition);
assertFalse(condition);

// Same reference
assertSame(expected, actual);
assertNotSame(expected, actual);

// Array equality
assertArrayEquals(expectedArray, actualArray);

// Iterable equality
assertIterableEquals(expectedList, actualList);
```

### Exception Assertions

```java
// Assert exception is thrown
@Test
void shouldThrowWhenInvalid() {
    assertThrows(IllegalArgumentException.class, () -> {
        service.process(null);
    });
}

// Assert exception with message check
@Test
void shouldThrowWithMessage() {
    Exception exception = assertThrows(IllegalArgumentException.class, () -> {
        service.process(null);
    });
    assertTrue(exception.getMessage().contains("cannot be null"));
}

// Assert no exception
@Test
void shouldNotThrow() {
    assertDoesNotThrow(() -> service.process(validInput));
}
```

### Grouped Assertions

```java
@Test
void shouldValidateAllProperties() {
    User user = service.getUser(1L);

    assertAll("user properties",
        () -> assertEquals("John", user.getName()),
        () -> assertEquals("john@example.com", user.getEmail()),
        () -> assertTrue(user.isActive()),
        () -> assertNotNull(user.getCreatedAt())
    );
}
```

### Timeout Assertions

```java
@Test
void shouldCompleteWithinTimeout() {
    assertTimeout(Duration.ofSeconds(2), () -> {
        service.longRunningOperation();
    });
}

// Preemptively abort if timeout exceeded
@Test
void shouldAbortOnTimeout() {
    assertTimeoutPreemptively(Duration.ofMillis(100), () -> {
        service.operation();
    });
}
```

---

## Parameterized Tests

### Value Source

```java
@ParameterizedTest
@ValueSource(strings = {"apple", "banana", "cherry"})
void shouldAcceptValidFruits(String fruit) {
    assertTrue(validator.isValidFruit(fruit));
}

@ParameterizedTest
@ValueSource(ints = {1, 5, 10, 100})
void shouldAcceptPositiveNumbers(int number) {
    assertTrue(validator.isPositive(number));
}
```

### CSV Source

```java
@ParameterizedTest
@CsvSource({
    "1, 2, 3",
    "5, 5, 10",
    "-1, 1, 0"
})
void shouldAddNumbers(int a, int b, int expected) {
    assertEquals(expected, calculator.add(a, b));
}
```

### Method Source

```java
@ParameterizedTest
@MethodSource("provideUsersForValidation")
void shouldValidateUser(User user, boolean expected) {
    assertEquals(expected, validator.isValid(user));
}

static Stream<Arguments> provideUsersForValidation() {
    return Stream.of(
        Arguments.of(new User("John", "john@email.com"), true),
        Arguments.of(new User("", "invalid"), false),
        Arguments.of(null, false)
    );
}
```

### Null and Empty Source

```java
@ParameterizedTest
@NullAndEmptySource
@ValueSource(strings = {"  ", "\t", "\n"})
void shouldRejectBlankStrings(String input) {
    assertFalse(validator.isValid(input));
}
```

---

## Lifecycle Hooks

```java
class LifecycleTest {

    @BeforeAll
    static void setUpClass() {
        // Runs once before all tests
        // Must be static
    }

    @AfterAll
    static void tearDownClass() {
        // Runs once after all tests
        // Must be static
    }

    @BeforeEach
    void setUp() {
        // Runs before each test method
    }

    @AfterEach
    void tearDown() {
        // Runs after each test method
    }
}
```

---

## Naming Convention

Follow pattern: `{MethodName}_Should{Behavior}_When{Condition}`

```java
void findById_ShouldReturnUser_WhenUserExists()
void findById_ShouldReturnEmpty_WhenUserNotFound()
void findById_ShouldThrowException_WhenIdIsNull()
void save_ShouldPersistUser_WhenValidUser()
void delete_ShouldRemoveUser_WhenUserExists()
void calculateTotal_ShouldReturnZero_WhenCartIsEmpty()
```

Alternative with @DisplayName:

```java
@Test
@DisplayName("findById returns user when user exists")
void findByIdReturnsUserWhenExists() { ... }
```

---

## Test Assumptions

Skip tests conditionally:

```java
@Test
void testOnlyOnLinux() {
    assumeTrue(System.getProperty("os.name").contains("Linux"));
    // Test runs only on Linux
}

@Test
void testWithAssumption() {
    assumingThat(
        System.getenv("CI") != null,
        () -> {
            // Additional assertions for CI environment
        }
    );
    // These assertions run always
    assertEquals(expected, actual);
}
```

---

## Disabled Tests

```java
@Disabled("Temporarily disabled until bug #123 is fixed")
@Test
void temporarilyDisabledTest() { ... }

@DisabledIf("isOnWindows")
@Test
void notOnWindows() { ... }

boolean isOnWindows() {
    return System.getProperty("os.name").contains("Windows");
}
```
