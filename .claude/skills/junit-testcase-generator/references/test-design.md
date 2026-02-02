# Test Case Design Techniques

## Equivalence Partitioning

Divide inputs into groups where all values in a group should behave the same.

### Pattern

```
Input domain → Identify partitions → Select one value per partition
```

### Example: Age Validation (18-65)

| Partition | Values | Expected | Test Value |
|-----------|--------|----------|------------|
| Below minimum | < 18 | Invalid | 17 |
| Valid range | 18-65 | Valid | 30 |
| Above maximum | > 65 | Invalid | 66 |
| Negative | < 0 | Invalid | -1 |
| Null/Empty | null | Exception | null |

```java
@ParameterizedTest
@CsvSource({
    "17, false",   // Below minimum
    "30, true",    // Valid range
    "66, false",   // Above maximum
    "-1, false"    // Negative
})
void validateAge_ShouldReturnExpected(int age, boolean expected) {
    assertEquals(expected, validator.isValidAge(age));
}

@Test
void validateAge_ShouldThrow_WhenNull() {
    assertThrows(NullPointerException.class,
        () -> validator.isValidAge(null));
}
```

---

## Boundary Value Analysis

Test at the edges of partitions where bugs commonly occur.

### Pattern

```
For boundary B: Test B-1, B, B+1
```

### Example: Age Validation (18-65)

| Boundary | Test Values | Expected |
|----------|-------------|----------|
| Min-1 | 17 | Invalid |
| Min | 18 | Valid |
| Min+1 | 19 | Valid |
| Max-1 | 64 | Valid |
| Max | 65 | Valid |
| Max+1 | 66 | Invalid |

```java
@ParameterizedTest
@CsvSource({
    // Minimum boundary
    "17, false",   // min - 1
    "18, true",    // min
    "19, true",    // min + 1
    // Maximum boundary
    "64, true",    // max - 1
    "65, true",    // max
    "66, false"    // max + 1
})
void validateAge_BoundaryValues(int age, boolean expected) {
    assertEquals(expected, validator.isValidAge(age));
}
```

---

## String Input Testing

### Partition Categories

| Category | Values | Test |
|----------|--------|------|
| Null | `null` | Handle/Throw |
| Empty | `""` | Handle/Reject |
| Whitespace only | `"   "`, `"\t"` | Handle/Reject |
| Single char | `"a"` | Accept/Reject |
| Normal | `"hello"` | Accept |
| Max length | `"a".repeat(maxLen)` | Accept |
| Over max | `"a".repeat(maxLen+1)` | Reject |
| Special chars | `"<script>"`, `"'; DROP TABLE"` | Sanitize |
| Unicode | `"日本語"`, `"émojis 🎉"` | Handle |

```java
@ParameterizedTest
@NullAndEmptySource
@ValueSource(strings = {"   ", "\t", "\n"})
void validateName_ShouldReject_WhenBlank(String name) {
    assertFalse(validator.isValidName(name));
}

@Test
void validateName_ShouldAccept_WhenNormal() {
    assertTrue(validator.isValidName("John Doe"));
}

@Test
void validateName_ShouldReject_WhenTooLong() {
    String longName = "a".repeat(101);
    assertFalse(validator.isValidName(longName));
}
```

---

## Collection Input Testing

### Partition Categories

| Category | Value | Test |
|----------|-------|------|
| Null | `null` | Handle/Throw |
| Empty | `Collections.emptyList()` | Handle edge case |
| Single element | `List.of(item)` | Process correctly |
| Multiple elements | `List.of(a, b, c)` | Process all |
| Large collection | `generate(1000)` | Performance/limits |
| Contains null | `Arrays.asList(a, null, b)` | Handle/Skip/Throw |
| Duplicates | `List.of(a, a, a)` | Handle correctly |

```java
@Test
void processItems_ShouldReturnEmpty_WhenEmptyList() {
    List<Result> results = service.processItems(Collections.emptyList());
    assertTrue(results.isEmpty());
}

@Test
void processItems_ShouldThrow_WhenNull() {
    assertThrows(NullPointerException.class,
        () -> service.processItems(null));
}

@Test
void processItems_ShouldProcessAll_WhenMultiple() {
    List<Item> items = List.of(item1, item2, item3);
    List<Result> results = service.processItems(items);
    assertEquals(3, results.size());
}

@Test
void processItems_ShouldHandleDuplicates() {
    List<Item> items = List.of(item1, item1, item1);
    List<Result> results = service.processItems(items);
    // Verify behavior with duplicates
}
```

---

## Numeric Input Testing

### Integer Boundaries

| Category | Value | Purpose |
|----------|-------|---------|
| Zero | `0` | Division, empty state |
| Negative | `-1`, `Integer.MIN_VALUE` | Sign handling |
| Positive | `1`, `Integer.MAX_VALUE` | Normal case, overflow |
| Typical | Middle values | Normal operation |

### Floating Point

| Category | Value | Purpose |
|----------|-------|---------|
| Zero | `0.0` | Division by zero |
| Negative zero | `-0.0` | IEEE special case |
| Positive/Negative | `1.5`, `-1.5` | Sign handling |
| Very small | `Double.MIN_VALUE` | Underflow |
| Very large | `Double.MAX_VALUE` | Overflow |
| NaN | `Double.NaN` | Not a number |
| Infinity | `Double.POSITIVE_INFINITY` | Overflow result |

```java
@ParameterizedTest
@ValueSource(doubles = {0.0, -0.0, Double.NaN,
    Double.POSITIVE_INFINITY, Double.NEGATIVE_INFINITY})
void calculate_ShouldHandleSpecialValues(double value) {
    // Verify behavior doesn't crash
    assertDoesNotThrow(() -> calculator.calculate(value));
}
```

---

## Date/Time Testing

### Important Cases

| Category | Value | Test |
|----------|-------|------|
| Null | `null` | Handle/Throw |
| Now | `LocalDate.now()` | Current date |
| Past | `LocalDate.of(2000, 1, 1)` | Historical |
| Future | `LocalDate.now().plusYears(10)` | Future dates |
| Leap year | `LocalDate.of(2024, 2, 29)` | Feb 29 handling |
| Month boundaries | Jan 31, Feb 28 | End of month |
| Year boundaries | Dec 31, Jan 1 | Year transitions |
| DST transitions | Specific dates | Time zone issues |
| Epoch | `Instant.EPOCH` | Unix epoch |

```java
@Test
void calculateAge_ShouldHandleLeapYear() {
    LocalDate leapBirthday = LocalDate.of(2000, 2, 29);
    int age = service.calculateAge(leapBirthday, LocalDate.of(2024, 2, 28));
    assertEquals(23, age);
}

@Test
void calculateAge_ShouldHandleFutureDate() {
    LocalDate future = LocalDate.now().plusDays(1);
    assertThrows(IllegalArgumentException.class,
        () -> service.calculateAge(future, LocalDate.now()));
}
```

---

## State-Based Testing

Test methods across different object states.

### Example: Order Processing

| State | Methods Available | Test |
|-------|-------------------|------|
| New | `addItem()`, `cancel()` | Add items, cancel |
| Pending | `submit()`, `cancel()` | Submit, cancel |
| Submitted | `approve()`, `reject()` | Approve, reject |
| Approved | `ship()` | Ship order |
| Shipped | `deliver()` | Complete delivery |
| Cancelled | None | No operations allowed |

```java
@Test
void ship_ShouldThrow_WhenOrderNotApproved() {
    Order order = new Order(); // New state
    order.addItem(item);
    order.submit();            // Pending -> Submitted

    // Try to ship without approval
    assertThrows(InvalidStateException.class,
        () -> order.ship());
}

@Test
void addItem_ShouldThrow_WhenOrderSubmitted() {
    Order order = createSubmittedOrder();

    assertThrows(InvalidStateException.class,
        () -> order.addItem(newItem));
}
```

---

## Error Path Testing

### Common Error Scenarios

| Error Type | Trigger | Expected |
|------------|---------|----------|
| Null input | Pass `null` | NullPointerException or graceful |
| Invalid format | Wrong data format | FormatException |
| Resource not found | Invalid ID | NotFoundException |
| Permission denied | Unauthorized access | AccessDeniedException |
| Timeout | Slow external call | TimeoutException |
| Network failure | Connection issue | ConnectionException |

```java
@Test
void findUser_ShouldThrowNotFound_WhenIdNotExists() {
    when(repository.findById(999L)).thenReturn(Optional.empty());

    assertThrows(UserNotFoundException.class,
        () -> service.findUser(999L));
}

@Test
void callExternalService_ShouldThrowTimeout_WhenSlow() {
    when(externalService.call(any()))
        .thenThrow(new TimeoutException("Timeout"));

    assertThrows(ServiceTimeoutException.class,
        () -> service.processExternal(data));
}
```

---

## Decision Table Testing

For methods with multiple conditions.

### Example: Discount Calculation

| Premium? | Order > $100 | Coupon? | Discount |
|----------|--------------|---------|----------|
| No | No | No | 0% |
| No | No | Yes | 5% |
| No | Yes | No | 10% |
| No | Yes | Yes | 15% |
| Yes | No | No | 10% |
| Yes | No | Yes | 15% |
| Yes | Yes | No | 20% |
| Yes | Yes | Yes | 25% |

```java
@ParameterizedTest
@CsvSource({
    "false, 50,  false, 0",
    "false, 50,  true,  5",
    "false, 150, false, 10",
    "false, 150, true,  15",
    "true,  50,  false, 10",
    "true,  50,  true,  15",
    "true,  150, false, 20",
    "true,  150, true,  25"
})
void calculateDiscount_DecisionTable(
        boolean isPremium, double orderAmount,
        boolean hasCoupon, int expectedDiscount) {

    Customer customer = new Customer(isPremium);
    Order order = new Order(orderAmount);

    int discount = service.calculateDiscount(customer, order, hasCoupon);

    assertEquals(expectedDiscount, discount);
}
```

---

## Test Case Checklist

For each method, consider:

- [ ] **Null inputs** - All nullable parameters
- [ ] **Empty inputs** - Empty strings, collections
- [ ] **Boundary values** - Min, max, edges
- [ ] **Invalid format** - Wrong data types/formats
- [ ] **Happy path** - Normal successful case
- [ ] **Error paths** - All exception scenarios
- [ ] **State transitions** - Valid and invalid
- [ ] **Concurrency** - Thread safety if applicable
- [ ] **Security** - Injection, access control
