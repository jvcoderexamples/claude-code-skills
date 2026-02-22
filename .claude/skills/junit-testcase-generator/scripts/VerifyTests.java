import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.regex.*;
import java.util.stream.Collectors;

/**
 * Verify generated JUnit tests using Maven.
 * Compiles tests, runs them, and reports errors for correction.
 *
 * Usage: java VerifyTests.java [test_folder] [options]
 *   test_folder              Path to test folder (default: src/test/java)
 *   --project-root <path>    Project root containing pom.xml (default: .)
 *   --compile-only           Only compile, don't run tests
 *   --test-class <name>      Run specific test class only
 *   --output <format>        Output format: json | summary (default: summary)
 */
public class VerifyTests {

    public static void main(String[] args) {
        String testFolder = "src/test/java";
        String projectRoot = ".";
        boolean compileOnly = false;
        String testClass = null;
        String output = "summary";

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--project-root":
                    projectRoot = args[++i];
                    break;
                case "--compile-only":
                    compileOnly = true;
                    break;
                case "--test-class":
                    testClass = args[++i];
                    break;
                case "--output":
                    output = args[++i];
                    break;
                default:
                    if (!args[i].startsWith("--")) testFolder = args[i];
                    break;
            }
        }

        // Check Maven project
        if (!Files.exists(Paths.get(projectRoot, "pom.xml"))) {
            System.err.println("Error: No pom.xml found at " + projectRoot);
            System.err.println("This skill requires a Maven project.");
            System.exit(1);
        }

        // Run specific test class
        if (testClass != null) {
            runSpecificTest(projectRoot, testClass, output);
            return;
        }

        // Verify all tests
        verifyAllTests(testFolder, projectRoot, !compileOnly, output);
    }

    static void runSpecificTest(String projectRoot, String testClass, String output) {
        System.out.println("Running test: " + testClass);
        String[] result = runMavenCommand(projectRoot, "test", "-Dtest=" + testClass, "-q");
        boolean success = "0".equals(result[0]);
        String mvnOutput = result[1];
        Map<String, Object> testResults = parseSurefireOutput(mvnOutput);

        if ("json".equals(output)) {
            Map<String, Object> json = new LinkedHashMap<>();
            json.put("success", success);
            json.put("results", testResults);
            json.put("output", truncate(mvnOutput, 2000));
            System.out.println(toJson(json));
        } else {
            if (success) {
                System.out.println("PASSED: " + testClass);
            } else {
                System.out.println("FAILED: " + testClass);
                System.out.println(truncate(mvnOutput, 1000));
            }
        }
        System.exit(success ? 0 : 1);
    }

    static void verifyAllTests(String testFolder, String projectRoot, boolean runTests, String output) {
        Path testPath = Paths.get(testFolder);
        if (!Files.exists(testPath)) {
            System.err.println("Error: Test folder does not exist: " + testFolder);
            System.exit(1);
        }

        // Find all test files
        List<Path> testFiles = findTestFiles(testPath);

        Map<String, Object> results = new LinkedHashMap<>();
        results.put("buildTool", "maven");
        results.put("totalTests", testFiles.size());
        List<Map<String, Object>> verified = new ArrayList<>();
        List<Map<String, Object>> compilationErrors = new ArrayList<>();
        List<Map<String, Object>> testFailures = new ArrayList<>();
        List<String> passed = new ArrayList<>();

        // First, compile all tests
        System.out.println("Compiling all tests with Maven...");
        String[] compileResult = runMavenCommand(projectRoot, "test-compile", "-q");
        boolean compileOk = "0".equals(compileResult[0]);
        String compileOutput = compileResult[1];

        if (!compileOk) {
            List<Map<String, Object>> errors = parseCompilationErrors(compileOutput);
            List<Map<String, Object>> errorSuggestions = new ArrayList<>();
            for (Map<String, Object> err : errors) {
                Map<String, Object> entry = new LinkedHashMap<>();
                entry.put("error", err);
                entry.put("suggestion", suggestFix(err));
                errorSuggestions.add(entry);
            }
            results.put("compilationErrors", errorSuggestions);
            results.put("status", "compilation_failed");
            results.put("rawOutput", truncate(compileOutput, 5000));
            printResults(results, output);
            return;
        }

        System.out.println("Compilation successful. Running tests...");

        // Verify each test file
        for (Path testFile : testFiles) {
            System.out.println("  Verifying: " + testFile.getFileName());
            Map<String, Object> verification = verifyTestFile(testFile, projectRoot, runTests);
            verified.add(verification);

            String status = (String) verification.get("status");
            if ("passed".equals(status)) {
                passed.add((String) verification.get("className"));
            } else if ("compilation_error".equals(status)) {
                compilationErrors.add(verification);
            } else if ("test_failure".equals(status)) {
                testFailures.add(verification);
            }
        }

        results.put("verified", verified);
        results.put("compilationErrors", compilationErrors);
        results.put("testFailures", testFailures);
        results.put("passed", passed);
        results.put("status", "complete");
        results.put("summary", Map.of(
                "total", testFiles.size(),
                "passed", passed.size(),
                "compilationErrors", compilationErrors.size(),
                "testFailures", testFailures.size()
        ));

        printResults(results, output);
    }

    @SuppressWarnings("unchecked")
    static void printResults(Map<String, Object> results, String output) {
        if ("json".equals(output)) {
            System.out.println(toJson(results));
        } else {
            System.out.println("\n=== Maven Test Verification Results ===");
            Map<String, Object> summary = (Map<String, Object>) results.get("summary");
            if (summary != null) {
                System.out.println("Total test files: " + summary.get("total"));
                System.out.println("  Passed:             " + summary.get("passed"));
                System.out.println("  Compilation errors: " + summary.get("compilationErrors"));
                System.out.println("  Test failures:      " + summary.get("testFailures"));

                List<Map<String, Object>> compErrors = (List<Map<String, Object>>) results.get("compilationErrors");
                if (compErrors != null && !compErrors.isEmpty()) {
                    System.out.println("\nCompilation Errors:");
                    compErrors.stream().limit(5).forEach(ce -> {
                        if (ce.containsKey("errors")) {
                            List<Map<String, Object>> errs = (List<Map<String, Object>>) ce.get("errors");
                            errs.stream().limit(3).forEach(err ->
                                    System.out.println("  - " + err.get("file") + ":" + err.get("line") + ": " +
                                            truncate((String) err.get("message"), 80)));
                        } else if (ce.containsKey("error")) {
                            Map<String, Object> err = (Map<String, Object>) ce.get("error");
                            System.out.println("  - " + err.get("file") + ":" + err.get("line") + ": " +
                                    truncate((String) err.get("message"), 80));
                            System.out.println("    Suggestion: " + ce.getOrDefault("suggestion", "N/A"));
                        }
                    });
                }

                List<Map<String, Object>> testFails = (List<Map<String, Object>>) results.get("testFailures");
                if (testFails != null && !testFails.isEmpty()) {
                    System.out.println("\nTest Failures:");
                    testFails.stream().limit(5).forEach(tf -> {
                        System.out.println("  - " + tf.get("className"));
                        Map<String, Object> tr = (Map<String, Object>) tf.get("testResults");
                        if (tr != null) {
                            List<Map<String, Object>> failures = (List<Map<String, Object>>) tr.get("failures");
                            if (failures != null) {
                                failures.stream().limit(2).forEach(f ->
                                        System.out.println("    " + f.get("method") + ": " +
                                                truncate((String) f.getOrDefault("message", "N/A"), 60)));
                            }
                        }
                    });
                }
            } else {
                System.out.println("Status: " + results.getOrDefault("status", "unknown"));
                if (results.containsKey("rawOutput")) {
                    System.out.println(truncate((String) results.get("rawOutput"), 2000));
                }
            }
        }
    }

    static Map<String, Object> verifyTestFile(Path testFile, String projectRoot, boolean runTests) {
        String content;
        try {
            content = Files.readString(testFile, StandardCharsets.UTF_8);
        } catch (IOException e) {
            return Map.of("file", testFile.toString(), "status", "error", "message", "Could not read file");
        }

        Matcher pkgMatcher = Pattern.compile("package\\s+([\\w.]+)\\s*;").matcher(content);
        Matcher clsMatcher = Pattern.compile("class\\s+(\\w+)").matcher(content);

        if (!clsMatcher.find()) {
            return Map.of("file", testFile.toString(), "status", "error", "message", "Could not parse test class name");
        }

        String pkg = pkgMatcher.find() ? pkgMatcher.group(1) : "";
        String className = clsMatcher.group(1);
        String fullClassName = pkg.isEmpty() ? className : pkg + "." + className;

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("file", testFile.toString());
        result.put("className", fullClassName);
        result.put("compiled", true);

        if (runTests) {
            String[] testResult = runMavenCommand(projectRoot, "test", "-Dtest=" + fullClassName, "-q");
            boolean testOk = "0".equals(testResult[0]);
            String testOutput = testResult[1];
            Map<String, Object> testResults = parseSurefireOutput(testOutput);

            if (testOk) {
                result.put("status", "passed");
                result.put("testResults", testResults);
            } else {
                result.put("status", "test_failure");
                result.put("testResults", testResults);
                result.put("output", truncate(testOutput, 2000));
            }
        } else {
            result.put("status", "compiled");
        }
        return result;
    }

    // ===== Maven command execution =====

    static String[] runMavenCommand(String projectRoot, String... mavenArgs) {
        List<String> cmd = new ArrayList<>();
        // Use mvn.cmd on Windows, mvn on Unix
        String os = System.getProperty("os.name", "").toLowerCase();
        if (os.contains("win")) {
            cmd.add("cmd");
            cmd.add("/c");
            cmd.add("mvn");
        } else {
            cmd.add("mvn");
        }
        cmd.addAll(Arrays.asList(mavenArgs));

        try {
            ProcessBuilder pb = new ProcessBuilder(cmd);
            pb.directory(new File(projectRoot));
            pb.redirectErrorStream(true);
            Process process = pb.start();

            StringBuilder output = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    output.append(line).append("\n");
                }
            }

            boolean finished = process.waitFor(300, TimeUnit.SECONDS);
            if (!finished) {
                process.destroyForcibly();
                return new String[]{"1", "Command timed out"};
            }

            return new String[]{String.valueOf(process.exitValue()), output.toString()};
        } catch (Exception e) {
            return new String[]{"1", "Error executing Maven: " + e.getMessage()};
        }
    }

    // ===== Output parsing =====

    static Map<String, Object> parseSurefireOutput(String output) {
        Map<String, Object> results = new LinkedHashMap<>();
        results.put("total", 0);
        results.put("passed", 0);
        results.put("failed", 0);
        results.put("errors", 0);
        results.put("skipped", 0);
        results.put("failures", new ArrayList<>());

        // Parse summary: Tests run: X, Failures: Y, Errors: Z, Skipped: W
        Matcher m = Pattern.compile("Tests run:\\s*(\\d+),\\s*Failures:\\s*(\\d+),\\s*Errors:\\s*(\\d+),\\s*Skipped:\\s*(\\d+)")
                .matcher(output);
        if (m.find()) {
            int total = Integer.parseInt(m.group(1));
            int failed = Integer.parseInt(m.group(2));
            int errors = Integer.parseInt(m.group(3));
            int skipped = Integer.parseInt(m.group(4));
            results.put("total", total);
            results.put("failed", failed);
            results.put("errors", errors);
            results.put("skipped", skipped);
            results.put("passed", total - failed - errors - skipped);
        }

        // Extract failure details
        List<Map<String, String>> failures = new ArrayList<>();
        Matcher fm = Pattern.compile("(\\w+)\\(([^)]+)\\)\\s+Time elapsed:.*?<<<\\s*(FAILURE|ERROR)!\\s*\\n(.*?)(?=\\n\\n|\\n\\w+\\(|$)",
                Pattern.DOTALL).matcher(output);
        while (fm.find()) {
            failures.add(Map.of(
                    "method", fm.group(1),
                    "class", fm.group(2),
                    "type", fm.group(3),
                    "message", truncate(fm.group(4).trim(), 500)
            ));
        }
        results.put("failures", failures);
        return results;
    }

    static List<Map<String, Object>> parseCompilationErrors(String output) {
        List<Map<String, Object>> errors = new ArrayList<>();
        Set<String> seen = new HashSet<>();

        // Pattern: [ERROR] /path/File.java:[line,col] error: message
        Matcher m1 = Pattern.compile("\\[ERROR\\]\\s*([^:\\[\\]]+\\.java):\\[(\\d+),(\\d+)\\]\\s*(?:error:)?\\s*(.+)",
                Pattern.MULTILINE).matcher(output);
        while (m1.find()) {
            String key = m1.group(1).trim() + ":" + m1.group(2);
            if (seen.add(key)) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("file", m1.group(1).trim());
                err.put("line", Integer.parseInt(m1.group(2)));
                err.put("column", Integer.parseInt(m1.group(3)));
                err.put("message", m1.group(4).trim());
                errors.add(err);
            }
        }

        // Alternative: [ERROR] /path/File.java:line: error: message
        Matcher m2 = Pattern.compile("\\[ERROR\\]\\s*([^:\\[\\]]+\\.java):(\\d+):\\s*(?:error:)?\\s*(.+)",
                Pattern.MULTILINE).matcher(output);
        while (m2.find()) {
            String key = m2.group(1).trim() + ":" + m2.group(2);
            if (seen.add(key)) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("file", m2.group(1).trim());
                err.put("line", Integer.parseInt(m2.group(2)));
                err.put("column", 0);
                err.put("message", m2.group(3).trim());
                errors.add(err);
            }
        }

        return errors;
    }

    static String categorizeError(Map<String, Object> error) {
        String msg = ((String) error.get("message")).toLowerCase();
        if (msg.contains("cannot find symbol")) {
            if (msg.contains("class")) return "missing_import";
            if (msg.contains("method")) return "wrong_method_name";
            if (msg.contains("variable")) return "wrong_variable";
        }
        if (msg.contains("incompatible types")) return "type_mismatch";
        if (msg.contains("cannot be applied")) return "wrong_arguments";
        if (msg.contains("is not visible") || msg.contains("has private access")) return "access_modifier";
        if (msg.contains("package does not exist")) return "missing_dependency";
        if (msg.contains("unreported exception")) return "unhandled_exception";
        if (msg.contains("cannot access")) return "missing_import";
        if (msg.contains("non-static") && msg.contains("static")) return "static_context";
        return "unknown";
    }

    static String suggestFix(Map<String, Object> error) {
        String category = categorizeError(error);
        switch (category) {
            case "missing_import": return "Add missing import statement. Check if class exists in classpath.";
            case "wrong_method_name": return "Verify method name matches source class. Check spelling and parameters.";
            case "wrong_variable": return "Check variable name exists in scope. May need to declare or rename.";
            case "type_mismatch": return "Fix type mismatch. Check expected vs actual types in assignment/return.";
            case "wrong_arguments": return "Method arguments don't match signature. Check parameter types and count.";
            case "access_modifier": return "Cannot access private member directly. Use reflection for testing.";
            case "missing_dependency": return "Add missing dependency to pom.xml.";
            case "unhandled_exception": return "Add throws clause or try-catch block.";
            case "static_context": return "Static method trying to access non-static member. Fix context.";
            default: return "Review error message and fix accordingly.";
        }
    }

    static List<Path> findTestFiles(Path testPath) {
        List<Path> files = new ArrayList<>();
        try {
            Files.walkFileTree(testPath, new SimpleFileVisitor<>() {
                @Override
                public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                    if (file.getFileName().toString().endsWith("Test.java")) {
                        files.add(file);
                    }
                    return FileVisitResult.CONTINUE;
                }
            });
        } catch (IOException e) {
            System.err.println("Error scanning test folder: " + e.getMessage());
        }
        return files;
    }

    static String truncate(String s, int max) {
        if (s == null) return "";
        return s.length() <= max ? s : s.substring(0, max) + "...";
    }

    // ===== JSON utilities (no external deps) =====

    static String toJson(Object obj) {
        StringBuilder sb = new StringBuilder();
        writeJson(obj, sb, 0);
        return sb.toString();
    }

    @SuppressWarnings("unchecked")
    static void writeJson(Object obj, StringBuilder sb, int indent) {
        if (obj == null) {
            sb.append("null");
        } else if (obj instanceof String) {
            sb.append("\"").append(escapeJson((String) obj)).append("\"");
        } else if (obj instanceof Number || obj instanceof Boolean) {
            sb.append(obj);
        } else if (obj instanceof Map) {
            Map<String, Object> map = (Map<String, Object>) obj;
            sb.append("{\n");
            Iterator<Map.Entry<String, Object>> it = map.entrySet().iterator();
            while (it.hasNext()) {
                Map.Entry<String, Object> entry = it.next();
                sb.append("  ".repeat(indent + 1)).append("\"").append(escapeJson(entry.getKey())).append("\": ");
                writeJson(entry.getValue(), sb, indent + 1);
                if (it.hasNext()) sb.append(",");
                sb.append("\n");
            }
            sb.append("  ".repeat(indent)).append("}");
        } else if (obj instanceof List) {
            List<Object> list = (List<Object>) obj;
            if (list.isEmpty()) {
                sb.append("[]");
            } else {
                sb.append("[\n");
                for (int i = 0; i < list.size(); i++) {
                    sb.append("  ".repeat(indent + 1));
                    writeJson(list.get(i), sb, indent + 1);
                    if (i < list.size() - 1) sb.append(",");
                    sb.append("\n");
                }
                sb.append("  ".repeat(indent)).append("]");
            }
        } else {
            sb.append("\"").append(escapeJson(obj.toString())).append("\"");
        }
    }

    static String escapeJson(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t");
    }
}
