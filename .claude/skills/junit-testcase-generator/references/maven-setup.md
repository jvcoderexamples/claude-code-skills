# Maven Setup Reference

Required pom.xml configuration for JUnit 5 + Mockito test generation.

> **Version note**: The versions below were current as of early 2025.
> Check [mvnrepository.com](https://mvnrepository.com) for the latest releases before pinning.

## Dependencies

```xml
<dependencies>
    <!-- JUnit 5 -->
    <dependency>
        <groupId>org.junit.jupiter</groupId>
        <artifactId>junit-jupiter</artifactId>
        <version>5.10.0</version>
        <scope>test</scope>
    </dependency>

    <!-- Mockito Core -->
    <dependency>
        <groupId>org.mockito</groupId>
        <artifactId>mockito-core</artifactId>
        <version>5.8.0</version>
        <scope>test</scope>
    </dependency>

    <!-- Mockito JUnit 5 Integration -->
    <dependency>
        <groupId>org.mockito</groupId>
        <artifactId>mockito-junit-jupiter</artifactId>
        <version>5.8.0</version>
        <scope>test</scope>
    </dependency>
</dependencies>
```

## Build Plugins

```xml
<build>
    <plugins>
        <!-- Maven Surefire Plugin — required to run JUnit 5 tests -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-surefire-plugin</artifactId>
            <version>3.2.5</version>
        </plugin>
    </plugins>
</build>
```

## Verification

After adding dependencies, confirm the project compiles with:

```
mvn test-compile -q
```

If this fails, check for version conflicts with existing Spring Boot or other BOM-managed test dependencies. Spring Boot projects may already manage JUnit 5 and Mockito versions via `spring-boot-starter-test` — in that case, omit the explicit versions.
