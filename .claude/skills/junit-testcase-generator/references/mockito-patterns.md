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

---

## MockedConstruction Initializer — doAnswer vs when — Learned 2026-02-22

**Context:** Stubbing a mock inside a `MockedConstruction` initializer lambda using `when(mock.method()).thenAnswer()` can silently fail — the answer is never invoked, causing assertions to fail.

**Problem:**
```java
mockConstruction(KafkaProducer.class,
    (mock, ctx) -> when(mock.send(any(), any()))
        .thenAnswer(inv -> { ... }));  // ❌ may not fire
```

**Fix:** Use `doAnswer(...).when(mock).method(...)` instead — this form is always reliable inside initializer lambdas:
```java
mockConstruction(KafkaProducer.class,
    (mock, ctx) -> doAnswer(inv -> {
        Callback cb = inv.getArgument(1);
        cb.onCompletion(meta, null);
        return CompletableFuture.completedFuture(meta);
    }).when(mock).send(any(ProducerRecord.class), any(Callback.class)));  // ✅
```

**Rule:** Always use `doAnswer(...).when(mock).method(...)` (not `when(mock.method()).thenAnswer(...)`) when stubbing inside a `MockedConstruction` initializer lambda.

---

## MockedStatic + Exception Construction — Learned 2026-02-22

**Context:** Constructing a `new SQLException(...)` (or any exception whose constructor calls a static method of the mocked class) *inside* the `MockedStatic` try block causes `UnfinishedStubbingException`.

**Problem:**
```java
try (MockedStatic<DriverManager> dm = mockStatic(DriverManager.class)) {
    dm.when(() -> DriverManager.getConnection(...))
      .thenThrow(new SQLException("msg")); // ❌ SQLException() calls DriverManager.getLogWriter()
}
```

**Fix:** Construct the exception **before** entering the `MockedStatic` try block:
```java
SQLException ex = new SQLException("msg"); // ✅ created outside mock scope
try (MockedStatic<DriverManager> dm = mockStatic(DriverManager.class)) {
    dm.when(() -> DriverManager.getConnection(...)).thenThrow(ex);
}
```

**Rule:** Any exception type that calls static methods of a mocked class inside its constructor must be instantiated outside the `MockedStatic` try block.

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

---

## Pre-Interrupt Pattern — Covering While-Condition "False" Branch — Learned 2026-02-22

**Context:** A `run()` method loops `while (!Thread.currentThread().isInterrupted())`. All existing tests exit via an exception path — the while condition is never evaluated as `false`. JaCoCo shows a missed branch at the while-condition line.

**Problem:**
```java
// Every existing test causes an exception INSIDE the loop body.
// The while condition is always evaluated as `true` first; it never returns `false`.
// Branch "while condition = false" is never covered.
```

**Fix:** Pre-set the interrupt flag before calling `run()`. The loop condition is evaluated once, returns `true` immediately, and the loop body is skipped entirely. Clean up the flag in `finally`.
```java
@Test
void run_ShouldExitImmediately_WhenThreadIsPreInterrupted() throws Exception {
    try (MockedStatic<DriverManager> dmStatic = mockStatic(DriverManager.class);
         MockedConstruction<KafkaProducer> kafkaCtor = mockConstruction(KafkaProducer.class)) {
        dmStatic.when(() -> DriverManager.getConnection(anyString(), anyString(), anyString()))
                .thenReturn(mock(Connection.class));
        Thread.currentThread().interrupt(); // ← pre-set flag
        new MySqlKafkaProducerThread().run();
    } finally {
        Thread.interrupted(); // clear flag so it doesn't leak to subsequent tests
    }
}
```

**Rule:** To cover the `while (!isInterrupted())` false branch, call `Thread.currentThread().interrupt()` before `run()` and clear it in `finally { Thread.interrupted(); }`. Verify that no logger or appender between class-init and the while check clears the interrupt flag (synchronous Log4j2 appenders do NOT clear it).

---

## Reflection on Private/Final Field to Control Sleep Duration — Learned 2026-02-22

**Context:** A `run()` method calls `Thread.sleep(pollIntervalMs)` where `pollIntervalMs` is a `private final long` loaded from config (e.g., 10 000 ms). Testing the sleep-call coverage path requires many loop iterations in a short test window.

**Problem:**
```java
// pollIntervalMs = 10_000L by default — Thread.sleep(10000) makes each iteration 10 s.
// A ScheduledExecutor interrupt after 400ms fires before the sleep call is even reached.
// Lines 100, 101, 170, 171 (sleep path) are never covered.
```

**Why `mockStatic(Thread.class)` is NOT allowed:**
```java
// Mockito 5 explicitly blocks java.lang.Thread statics:
// "It is not possible to mock static methods of java.lang.Thread to avoid
//  interfering with class loading what leads to infinite loops."
mockStatic(Thread.class); // ❌ throws MockitoException
```

**Fix:** Use reflection to set `pollIntervalMs = 0L` before calling `run()`. With sleep(0), the loop iterates thousands of times in 400 ms.
```java
MySqlKafkaProducerThread thread = new MySqlKafkaProducerThread();
Field pollField = MySqlKafkaProducerThread.class.getDeclaredField("pollIntervalMs");
pollField.setAccessible(true);
pollField.set(thread, 0L); // ← sleep(0) returns immediately

Thread testThread = Thread.currentThread();
ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();
scheduler.schedule(() -> testThread.interrupt(), 400, TimeUnit.MILLISECONDS);
try {
    thread.run(); // loop runs many iterations; sleep() path covered
} finally {
    Thread.interrupted();
    scheduler.shutdownNow();
}
```

**Rule:** Never use `mockStatic(Thread.class)`. To test code paths gated behind `Thread.sleep(N)`, set the sleep-duration field to 0 via `Field.setAccessible(true)` + `field.set(instance, 0L)`, then interrupt after a short delay.

---

## MockedStatic Thread-Scope: catch(Exception) Must Run on Test Thread — Learned 2026-02-22

**Context:** A `catch(Exception e)` block exists after `catch(SQLException e)` inside `run()`. A test spawns a new `Thread` to run the subject class, intending the generic exception to be thrown. `MockedStatic<DriverManager>` was set up on the test thread.

**Problem:**
```java
// MockedStatic is scoped to the CREATING thread.
// Code running on a NEW thread does NOT see the MockedStatic from the test thread.
// Real DriverManager.getConnection() is called → throws real SQLException → caught
// by catch(SQLException e), not catch(Exception e). Target branch is never hit.
new Thread(() -> producerThread.run()).start(); // ❌ wrong thread — MockedStatic not active
```

**Fix:** Run `producerThread.run()` **directly on the test thread** inside the `try (MockedStatic...)` block:
```java
try (MockedStatic<DriverManager> dmStatic = mockStatic(DriverManager.class);
     MockedConstruction<KafkaProducer> kafkaCtor = mockConstruction(KafkaProducer.class)) {
    // Stub getConnection to return a connection whose prepareStatement throws RuntimeException
    Connection mockConn = mock(Connection.class);
    when(mockConn.prepareStatement(anyString()))
            .thenThrow(new RuntimeException("unexpected error"));
    dmStatic.when(() -> DriverManager.getConnection(anyString(), anyString(), anyString()))
            .thenReturn(mockConn);
    new MySqlKafkaProducerThread().run(); // ✅ same thread — MockedStatic is active
}
```

**Rule:** Both `MockedStatic` and `MockedConstruction` are scoped to the thread that creates them. Always run the subject under test **on the test thread itself** — never spawn a new Thread inside a `try (MockedStatic...)` block unless you accept that the static mock will NOT be visible to the new thread.
