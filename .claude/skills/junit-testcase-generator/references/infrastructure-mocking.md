# Infrastructure Mocking Patterns

## Table of Contents

- [Logger Mocking (SLF4J + Log4j2)](#logger-mocking)
- [Logger Guard Testing](#logger-guard-testing)
- [Database Call Mocking](#database-call-mocking)
- [API Call Mocking](#api-call-mocking)
- [Kafka Mocking](#kafka-mocking)

---

## Logger Mocking

### Setup: Mock SLF4J Logger via Field Injection

```java
import org.slf4j.Logger;
import java.lang.reflect.Field;

@ExtendWith(MockitoExtension.class)
class MyServiceTest {

    @Mock
    private Logger logger;

    @InjectMocks
    private MyService underTest;

    @BeforeEach
    void setUp() throws Exception {
        // Inject mock logger into the private static final logger field
        Field loggerField = MyService.class.getDeclaredField("logger");
        loggerField.setAccessible(true);

        // Remove final modifier
        Field modifiersField = Field.class.getDeclaredField("modifiers");
        modifiersField.setAccessible(true);
        modifiersField.setInt(loggerField, loggerField.getModifiers() & ~java.lang.reflect.Modifier.FINAL);

        loggerField.set(null, logger);
    }
}
```

### Alternative: MockedStatic for LoggerFactory

```java
@Test
void shouldMockLogger() {
    Logger mockLogger = mock(Logger.class);

    try (MockedStatic<LoggerFactory> loggerFactory = mockStatic(LoggerFactory.class)) {
        loggerFactory.when(() -> LoggerFactory.getLogger(MyService.class))
                     .thenReturn(mockLogger);

        // Create instance AFTER mocking LoggerFactory
        MyService service = new MyService();

        when(mockLogger.isDebugEnabled()).thenReturn(true);
        service.doSomething();

        verify(mockLogger).debug(anyString(), any());
    }
}
```

---

## Logger Guard Testing

### CRITICAL: Test Both true AND false Paths

Source code pattern:
```java
if (logger.isDebugEnabled()) {
    logger.debug("Processing item: {}", item.toDetailedString());
}
if (logger.isInfoEnabled()) {
    logger.info("Operation completed for: {}", result.getSummary());
}
```

### Test: isDebugEnabled() = TRUE

```java
@Test
void process_ShouldLogDebugMessage_WhenDebugEnabled() {
    when(logger.isDebugEnabled()).thenReturn(true);

    underTest.process(testItem);

    verify(logger).isDebugEnabled();
    verify(logger).debug(eq("Processing item: {}"), anyString());
}
```

### Test: isDebugEnabled() = FALSE

```java
@Test
void process_ShouldSkipDebugLog_WhenDebugDisabled() {
    when(logger.isDebugEnabled()).thenReturn(false);

    underTest.process(testItem);

    verify(logger).isDebugEnabled();
    verify(logger, never()).debug(anyString());
    verify(logger, never()).debug(anyString(), any());
    verify(logger, never()).debug(anyString(), any(), any());
}
```

### Test: isInfoEnabled() = TRUE

```java
@Test
void process_ShouldLogInfoMessage_WhenInfoEnabled() {
    when(logger.isInfoEnabled()).thenReturn(true);

    underTest.process(testItem);

    verify(logger).isInfoEnabled();
    verify(logger).info(eq("Operation completed for: {}"), anyString());
}
```

### Test: isInfoEnabled() = FALSE

```java
@Test
void process_ShouldSkipInfoLog_WhenInfoDisabled() {
    when(logger.isInfoEnabled()).thenReturn(false);

    underTest.process(testItem);

    verify(logger).isInfoEnabled();
    verify(logger, never()).info(anyString());
    verify(logger, never()).info(anyString(), any());
}
```

### Test: isTraceEnabled() = FALSE

```java
@Test
void process_ShouldSkipTraceLog_WhenTraceDisabled() {
    when(logger.isTraceEnabled()).thenReturn(false);

    underTest.process(testItem);

    verify(logger, never()).trace(anyString());
    verify(logger, never()).trace(anyString(), any());
}
```

### Combined: Multiple Logger Guards in One Method

```java
@Test
void process_ShouldOnlyLogInfo_WhenDebugDisabledInfoEnabled() {
    when(logger.isDebugEnabled()).thenReturn(false);
    when(logger.isInfoEnabled()).thenReturn(true);

    underTest.process(testItem);

    verify(logger, never()).debug(anyString(), any());
    verify(logger).info(anyString(), any());
}
```

---

## Database Call Mocking

### JPA Repository Mocking

```java
@Mock
private UserRepository userRepository;

@Test
void findUser_ShouldReturnUser_WhenExists() {
    User expected = new User(1L, "John");
    when(userRepository.findById(1L)).thenReturn(Optional.of(expected));

    User result = underTest.findUser(1L);

    assertEquals("John", result.getName());
    verify(userRepository).findById(1L);
}

@Test
void findUser_ShouldThrow_WhenNotFound() {
    when(userRepository.findById(anyLong())).thenReturn(Optional.empty());

    assertThrows(UserNotFoundException.class, () -> underTest.findUser(999L));
}

@Test
void saveUser_ShouldReturnSaved_WhenValid() {
    User input = new User(null, "Jane");
    User saved = new User(1L, "Jane");
    when(userRepository.save(any(User.class))).thenReturn(saved);

    User result = underTest.saveUser(input);

    assertEquals(1L, result.getId());
    verify(userRepository).save(input);
}

@Test
void deleteUser_ShouldCallRepository_WhenExists() {
    when(userRepository.existsById(1L)).thenReturn(true);
    doNothing().when(userRepository).deleteById(1L);

    underTest.deleteUser(1L);

    verify(userRepository).deleteById(1L);
}

@Test
void saveUser_ShouldThrow_WhenDbError() {
    when(userRepository.save(any()))
        .thenThrow(new DataAccessException("Connection refused") {});

    assertThrows(DataAccessException.class, () -> underTest.saveUser(new User()));
}
```

### JdbcTemplate Mocking

```java
@Mock
private JdbcTemplate jdbcTemplate;

@Test
void findByName_ShouldReturnList() {
    List<User> expected = List.of(new User(1L, "John"));
    when(jdbcTemplate.query(anyString(), any(RowMapper.class), eq("John")))
        .thenReturn(expected);

    List<User> result = underTest.findByName("John");

    assertEquals(1, result.size());
}

@Test
void update_ShouldReturnRowCount() {
    when(jdbcTemplate.update(anyString(), any(Object[].class))).thenReturn(1);

    int rows = underTest.updateUser(1L, "NewName");

    assertEquals(1, rows);
}
```

---

## API Call Mocking

### RestTemplate Mocking

```java
@Mock
private RestTemplate restTemplate;

@Test
void fetchData_ShouldReturnResponse_WhenSuccess() {
    ResponseEntity<ApiResponse> response = ResponseEntity.ok(new ApiResponse("data"));
    when(restTemplate.exchange(anyString(), eq(HttpMethod.GET), any(), eq(ApiResponse.class)))
        .thenReturn(response);

    ApiResponse result = underTest.fetchData("endpoint");

    assertNotNull(result);
    assertEquals("data", result.getBody());
}

@Test
void fetchData_ShouldThrow_WhenServerError() {
    when(restTemplate.exchange(anyString(), eq(HttpMethod.GET), any(), eq(ApiResponse.class)))
        .thenThrow(new HttpServerErrorException(HttpStatus.INTERNAL_SERVER_ERROR));

    assertThrows(HttpServerErrorException.class, () -> underTest.fetchData("endpoint"));
}

@Test
void fetchData_ShouldThrow_WhenTimeout() {
    when(restTemplate.exchange(anyString(), eq(HttpMethod.GET), any(), eq(ApiResponse.class)))
        .thenThrow(new ResourceAccessException("Connection timed out"));

    assertThrows(ResourceAccessException.class, () -> underTest.fetchData("endpoint"));
}
```

### WebClient Mocking

```java
@Mock
private WebClient webClient;
@Mock
private WebClient.RequestHeadersUriSpec requestHeadersUriSpec;
@Mock
private WebClient.RequestHeadersSpec requestHeadersSpec;
@Mock
private WebClient.ResponseSpec responseSpec;

@Test
void fetchAsync_ShouldReturnData() {
    when(webClient.get()).thenReturn(requestHeadersUriSpec);
    when(requestHeadersUriSpec.uri(anyString())).thenReturn(requestHeadersSpec);
    when(requestHeadersSpec.retrieve()).thenReturn(responseSpec);
    when(responseSpec.bodyToMono(ApiResponse.class)).thenReturn(Mono.just(new ApiResponse("data")));

    Mono<ApiResponse> result = underTest.fetchAsync("/api/data");

    StepVerifier.create(result)
        .expectNextMatches(r -> "data".equals(r.getBody()))
        .verifyComplete();
}
```

### Feign Client Mocking

```java
@Mock
private UserFeignClient userFeignClient;

@Test
void getUser_ShouldReturnUser_WhenFeignSucceeds() {
    UserDto expected = new UserDto(1L, "John");
    when(userFeignClient.getUserById(1L)).thenReturn(expected);

    UserDto result = underTest.getUser(1L);

    assertEquals("John", result.getName());
}

@Test
void getUser_ShouldThrow_WhenFeignFails() {
    when(userFeignClient.getUserById(anyLong()))
        .thenThrow(new FeignException.NotFound("Not found", mock(Request.class), null, null));

    assertThrows(FeignException.NotFound.class, () -> underTest.getUser(999L));
}
```

---

## Kafka Mocking

### KafkaTemplate (Producer) Mocking

```java
@Mock
private KafkaTemplate<String, String> kafkaTemplate;

@Test
void sendMessage_ShouldCallKafkaTemplate() {
    CompletableFuture<SendResult<String, String>> future = new CompletableFuture<>();
    future.complete(mock(SendResult.class));

    when(kafkaTemplate.send(anyString(), anyString())).thenReturn(future);

    underTest.sendMessage("test-topic", "test-message");

    verify(kafkaTemplate).send("test-topic", "test-message");
}

@Test
void sendMessage_ShouldCallKafkaTemplate_WithKey() {
    CompletableFuture<SendResult<String, String>> future = new CompletableFuture<>();
    future.complete(mock(SendResult.class));

    when(kafkaTemplate.send(anyString(), anyString(), anyString())).thenReturn(future);

    underTest.sendMessage("test-topic", "key-1", "test-message");

    verify(kafkaTemplate).send("test-topic", "key-1", "test-message");
}

@Test
void sendMessage_ShouldHandleFailure_WhenKafkaUnavailable() {
    CompletableFuture<SendResult<String, String>> future = new CompletableFuture<>();
    future.completeExceptionally(new KafkaException("Broker not available"));

    when(kafkaTemplate.send(anyString(), anyString())).thenReturn(future);

    // Test depends on how the class handles the future failure
    // Option A: If it throws
    assertThrows(KafkaException.class, () -> underTest.sendMessageSync("topic", "msg"));

    // Option B: If it has a callback
    underTest.sendMessageAsync("topic", "msg");
    verify(kafkaTemplate).send("topic", "msg");
}
```

### KafkaProducer (Non-Spring) Mocking

```java
@Mock
private KafkaProducer<String, String> kafkaProducer;

@Test
void produce_ShouldSendRecord() {
    Future<RecordMetadata> future = mock(Future.class);
    when(kafkaProducer.send(any(ProducerRecord.class))).thenReturn(future);

    underTest.produce("topic", "key", "value");

    ArgumentCaptor<ProducerRecord<String, String>> captor = ArgumentCaptor.forClass(ProducerRecord.class);
    verify(kafkaProducer).send(captor.capture());
    assertEquals("topic", captor.getValue().topic());
    assertEquals("key", captor.getValue().key());
    assertEquals("value", captor.getValue().value());
}

@Test
void produce_ShouldHandleCallback_OnSuccess() {
    doAnswer(invocation -> {
        ProducerRecord<String, String> record = invocation.getArgument(0);
        Callback callback = invocation.getArgument(1);
        callback.onCompletion(new RecordMetadata(new TopicPartition("topic", 0), 0, 0, 0, 0, 0), null);
        return mock(Future.class);
    }).when(kafkaProducer).send(any(ProducerRecord.class), any(Callback.class));

    underTest.produceWithCallback("topic", "key", "value");

    verify(kafkaProducer).send(any(ProducerRecord.class), any(Callback.class));
}

@Test
void produce_ShouldHandleCallback_OnError() {
    doAnswer(invocation -> {
        Callback callback = invocation.getArgument(1);
        callback.onCompletion(null, new KafkaException("Send failed"));
        return mock(Future.class);
    }).when(kafkaProducer).send(any(ProducerRecord.class), any(Callback.class));

    underTest.produceWithCallback("topic", "key", "value");

    // Verify error handling behavior
}
```

### KafkaConsumer / @KafkaListener Mocking

```java
// For classes with @KafkaListener, test the listener method directly
@ExtendWith(MockitoExtension.class)
class MyKafkaListenerTest {

    @Mock
    private MessageService messageService;

    @InjectMocks
    private MyKafkaListener underTest;

    @Test
    void onMessage_ShouldProcessMessage_WhenValid() {
        ConsumerRecord<String, String> record =
            new ConsumerRecord<>("test-topic", 0, 0L, "key", "{\"data\":\"value\"}");

        underTest.onMessage(record);

        verify(messageService).process(any());
    }

    @Test
    void onMessage_ShouldHandleDeserializationError() {
        ConsumerRecord<String, String> record =
            new ConsumerRecord<>("test-topic", 0, 0L, "key", "invalid-json");

        // Depending on error handling strategy
        assertThrows(JsonParseException.class, () -> underTest.onMessage(record));
        // OR
        underTest.onMessage(record);
        verify(messageService, never()).process(any());
    }

    @Test
    void onMessage_ShouldHandleNullValue() {
        ConsumerRecord<String, String> record =
            new ConsumerRecord<>("test-topic", 0, 0L, "key", null);

        underTest.onMessage(record);

        verify(messageService, never()).process(any());
    }
}
```

### Kafka Acknowledgment Mocking

```java
@Mock
private Acknowledgment acknowledgment;

@Test
void onMessage_ShouldAcknowledge_WhenProcessed() {
    ConsumerRecord<String, String> record =
        new ConsumerRecord<>("topic", 0, 0L, "key", "value");

    underTest.onMessage(record, acknowledgment);

    verify(acknowledgment).acknowledge();
}

@Test
void onMessage_ShouldNotAcknowledge_WhenProcessingFails() {
    ConsumerRecord<String, String> record =
        new ConsumerRecord<>("topic", 0, 0L, "key", "bad-value");

    doThrow(new RuntimeException("Process failed"))
        .when(messageService).process(any());

    assertThrows(RuntimeException.class, () -> underTest.onMessage(record, acknowledgment));

    verify(acknowledgment, never()).acknowledge();
}
```
