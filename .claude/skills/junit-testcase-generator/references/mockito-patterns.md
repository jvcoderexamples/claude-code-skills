# Mockito Patterns Reference

## Essential Imports

```java
import org.mockito.Mock;
import org.mockito.InjectMocks;
import org.mockito.Spy;
import org.mockito.Captor;
import org.mockito.ArgumentCaptor;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
```

---

## Setup Patterns

### With JUnit 5 Extension (Recommended)

```java
@ExtendWith(MockitoExtension.class)
class ServiceTest {

    @Mock
    private Repository repository;

    @Mock
    private ExternalService externalService;

    @InjectMocks
    private Service underTest;

    @Test
    void testMethod() {
        // Mocks are ready to use
    }
}
```

### Manual Setup

```java
class ServiceTest {

    private Repository repository;
    private Service underTest;

    @BeforeEach
    void setUp() {
        repository = mock(Repository.class);
        underTest = new Service(repository);
    }
}
```

---

## Stubbing (when/thenReturn)

### Basic Stubbing

```java
// Return value
when(repository.findById(1L)).thenReturn(Optional.of(user));

// Return null
when(repository.findById(999L)).thenReturn(Optional.empty());

// Multiple calls return different values
when(repository.count())
    .thenReturn(0)
    .thenReturn(1)
    .thenReturn(2);

// Throw exception
when(repository.save(null))
    .thenThrow(new IllegalArgumentException("User cannot be null"));
```

### Argument Matchers

```java
// Any argument of type
when(repository.findById(anyLong())).thenReturn(Optional.of(user));
when(repository.findByName(anyString())).thenReturn(users);

// Any argument including null
when(service.process(any())).thenReturn(result);

// Specific types
when(repository.save(any(User.class))).thenReturn(savedUser);

// Multiple matchers (all arguments must use matchers)
when(service.calculate(anyInt(), anyDouble())).thenReturn(100.0);

// eq() for mixing specific values with matchers
when(service.process(eq("specific"), anyInt())).thenReturn(result);

// Null argument
when(service.process(isNull())).thenThrow(NullPointerException.class);
when(service.process(isNotNull())).thenReturn(result);

// Collection matchers
when(service.processAll(anyList())).thenReturn(results);
when(service.processMap(anyMap())).thenReturn(result);
```

### Answer (Dynamic Response)

```java
// Return based on input
when(repository.findById(anyLong())).thenAnswer(invocation -> {
    Long id = invocation.getArgument(0);
    return id > 0 ? Optional.of(new User(id)) : Optional.empty();
});

// Modify argument and return
when(repository.save(any(User.class))).thenAnswer(invocation -> {
    User user = invocation.getArgument(0);
    user.setId(1L);  // Simulate ID generation
    return user;
});
```

### Void Methods

```java
// Do nothing (default behavior)
doNothing().when(repository).delete(any());

// Throw exception on void method
doThrow(new RuntimeException("Database error"))
    .when(repository).delete(null);

// Execute code
doAnswer(invocation -> {
    User user = invocation.getArgument(0);
    System.out.println("Deleting: " + user);
    return null;
}).when(repository).delete(any());
```

---

## Verification

### Basic Verification

```java
// Method was called
verify(repository).save(user);

// Method was never called
verify(repository, never()).delete(any());

// Called exact number of times
verify(repository, times(3)).findById(anyLong());

// Called at least/at most
verify(repository, atLeast(1)).save(any());
verify(repository, atMost(5)).findById(anyLong());
verify(repository, atLeastOnce()).count();

// No more interactions
verifyNoMoreInteractions(repository);

// No interactions at all
verifyNoInteractions(unusedMock);
```

### Verification with Argument Capture

```java
@Captor
ArgumentCaptor<User> userCaptor;

@Test
void shouldSaveCorrectUser() {
    // Act
    service.createUser("John", "john@email.com");

    // Capture
    verify(repository).save(userCaptor.capture());

    // Assert on captured value
    User captured = userCaptor.getValue();
    assertEquals("John", captured.getName());
    assertEquals("john@email.com", captured.getEmail());
}

// Multiple captures
@Test
void shouldSaveMultipleUsers() {
    service.createUsers(List.of("John", "Jane"));

    verify(repository, times(2)).save(userCaptor.capture());

    List<User> allCaptured = userCaptor.getAllValues();
    assertEquals(2, allCaptured.size());
}
```

### Verification Order

```java
@Test
void shouldCallInOrder() {
    // Act
    service.processOrder(order);

    // Verify order
    InOrder inOrder = inOrder(repository, paymentService, emailService);
    inOrder.verify(repository).save(any());
    inOrder.verify(paymentService).process(any());
    inOrder.verify(emailService).sendConfirmation(any());
}
```

### Verification with Timeout

```java
// For async operations
verify(repository, timeout(1000)).save(any());
verify(repository, timeout(1000).times(2)).findById(anyLong());
```

---

## Static Method Mocking

### MockedStatic Pattern

```java
@Test
void shouldMockStaticMethod() {
    try (MockedStatic<Utility> mocked = mockStatic(Utility.class)) {
        // Setup static mock
        mocked.when(() -> Utility.generateId()).thenReturn("mock-id-123");
        mocked.when(() -> Utility.format(anyString()))
              .thenAnswer(inv -> "formatted: " + inv.getArgument(0));

        // Act - code that uses Utility.generateId()
        String result = service.createWithId();

        // Assert
        assertEquals("mock-id-123", result);

        // Verify static call
        mocked.verify(() -> Utility.generateId());
        mocked.verify(() -> Utility.format(anyString()), times(1));
    }
    // Static mock is reset after try block
}
```

### Static Void Methods

```java
@Test
void shouldMockStaticVoidMethod() {
    try (MockedStatic<Logger> mocked = mockStatic(Logger.class)) {
        // Do nothing on static void
        mocked.when(() -> Logger.log(anyString())).thenAnswer(inv -> null);

        // Or throw
        mocked.when(() -> Logger.log("error"))
              .thenThrow(new RuntimeException("Log failed"));

        // Act
        service.doSomething();

        // Verify
        mocked.verify(() -> Logger.log(anyString()), atLeastOnce());
    }
}
```

---

## Spy (Partial Mock)

```java
@Spy
private UserService userService = new UserService();

@Test
void shouldSpyOnRealObject() {
    // Real method is called by default
    User realResult = userService.findById(1L);

    // Override specific method
    doReturn(mockUser).when(userService).findById(2L);

    // Verify real calls
    verify(userService).findById(1L);
}
```

### Spy with Constructor Injection

```java
@Spy
@InjectMocks
private OrderService orderService;

@Test
void shouldUseSpyWithMocks() {
    // orderService has mocked dependencies but real methods
    doReturn(true).when(orderService).validateOrder(any());

    // Real processOrder uses mocked repository
    orderService.processOrder(order);
}
```

---

## Common Patterns for Different Scenarios

### Repository Testing

```java
@Test
void findById_ShouldReturnUser_WhenExists() {
    User expected = new User(1L, "John");
    when(repository.findById(1L)).thenReturn(Optional.of(expected));

    Optional<User> result = service.findById(1L);

    assertTrue(result.isPresent());
    assertEquals("John", result.get().getName());
}

@Test
void findById_ShouldReturnEmpty_WhenNotExists() {
    when(repository.findById(anyLong())).thenReturn(Optional.empty());

    Optional<User> result = service.findById(999L);

    assertTrue(result.isEmpty());
}
```

### External Service Calls

```java
@Test
void processPayment_ShouldReturnSuccess_WhenPaymentSucceeds() {
    PaymentResponse mockResponse = new PaymentResponse("success", "txn123");
    when(paymentGateway.charge(any())).thenReturn(mockResponse);

    PaymentResult result = service.processPayment(order);

    assertTrue(result.isSuccessful());
    verify(paymentGateway).charge(any(PaymentRequest.class));
}

@Test
void processPayment_ShouldHandleFailure_WhenGatewayFails() {
    when(paymentGateway.charge(any()))
        .thenThrow(new PaymentException("Gateway unavailable"));

    assertThrows(PaymentException.class,
        () -> service.processPayment(order));
}
```

### Callback/Event Testing

```java
@Test
void shouldTriggerCallback() {
    doAnswer(invocation -> {
        Callback callback = invocation.getArgument(1);
        callback.onSuccess("result");
        return null;
    }).when(asyncService).fetchData(any(), any());

    service.loadData();

    verify(resultHandler).handleResult("result");
}
```

---

## Strict vs Lenient Stubbing

```java
// Strict (default in JUnit 5) - fails if stub not used
@ExtendWith(MockitoExtension.class)
class StrictTest {
    // Unused stubs cause test failure
}

// Lenient mode for specific stub
@Test
void testWithLenientStub() {
    lenient().when(repository.findById(anyLong()))
             .thenReturn(Optional.of(user));
    // Won't fail if this stub isn't used
}

// Lenient mode for entire test
@MockitoSettings(strictness = Strictness.LENIENT)
class LenientTest { }
```

---

## Reset and Clear

```java
@AfterEach
void tearDown() {
    // Reset mock to initial state
    reset(repository);

    // Clear invocations but keep stubs
    clearInvocations(repository);
}
```
