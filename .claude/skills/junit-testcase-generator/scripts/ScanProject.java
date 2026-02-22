import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.time.Instant;
import java.util.*;
import java.util.regex.*;
import java.util.stream.Collectors;

/**
 * Scan Maven Java project source folder and identify classes needing unit tests.
 *
 * Stateless: reads source files, writes nothing. Output goes to stdout.
 * Equivalent to scan_project.py.
 *
 * Usage: java --source 11 ScanProject.java [source_folder] [options]
 *   source_folder           Path to Java source folder (default: src/main/java)
 *   --test-folder <path>    Path to test folder (default: src/test/java)
 *   --exclude <pattern>     Substring to exclude from relative paths (repeatable)
 *   --project-root <path>   Project root containing pom.xml (default: .)
 *   --output <format>       json | summary | pending  (default: summary)
 *
 * Exit codes: 0 = success, 1 = error
 */
public class ScanProject {

    public static void main(String[] args) {
        String sourceFolder = "src/main/java";
        String testFolder   = "src/test/java";
        String projectRoot  = ".";
        String output       = "summary";
        List<String> exclusions = new ArrayList<>();

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--test-folder":   testFolder  = args[++i]; break;
                case "--exclude":       exclusions.add(args[++i]); break;
                case "--project-root":  projectRoot = args[++i]; break;
                case "--output":        output      = args[++i]; break;
                default:
                    if (!args[i].startsWith("--")) sourceFolder = args[i];
                    break;
            }
        }

        Path pomPath = Paths.get(projectRoot, "pom.xml");
        if (!Files.exists(pomPath)) {
            System.err.println("Error: No pom.xml found at " + projectRoot +
                    ". This skill requires a Maven project.");
            System.exit(1);
        }

        Map<String, Boolean> deps    = checkMavenDependencies(pomPath);
        List<Map<String, Object>> classes = scanSourceFiles(sourceFolder, testFolder, exclusions);

        long totalClasses  = classes.size();
        long pendingCount  = classes.stream().filter(c -> "pending".equals(c.get("status"))).count();
        long existingCount = classes.stream().filter(c -> "existing".equals(c.get("status"))).count();
        long withStatic    = classes.stream().filter(c -> Boolean.TRUE.equals(c.get("hasStaticMethods"))).count();
        long withPrivate   = classes.stream().filter(c -> Boolean.TRUE.equals(c.get("hasPrivateMethods"))).count();

        switch (output) {
            case "json":
                Map<String, Object> root = new LinkedHashMap<>();
                root.put("scannedAt",         Instant.now().toString());
                root.put("sourceFolder",       sourceFolder);
                root.put("testFolder",         testFolder);
                root.put("buildTool",          "maven");
                root.put("mavenDependencies",  deps);
                Map<String, Object> summary = new LinkedHashMap<>();
                summary.put("totalClasses",       totalClasses);
                summary.put("pending",            pendingCount);
                summary.put("existingTests",      existingCount);
                summary.put("withStaticMethods",  withStatic);
                summary.put("withPrivateMethods", withPrivate);
                root.put("summary", summary);
                root.put("classes", classes);
                System.out.println(toJson(root));
                break;

            case "pending":
                List<Map<String, Object>> pending = classes.stream()
                        .filter(c -> "pending".equals(c.get("status")))
                        .collect(Collectors.toList());
                System.out.println(toJson(pending));
                break;

            default: // summary
                System.out.println("\n=== Maven Project Scan Results ===");
                System.out.println("Project root:  " + projectRoot);
                System.out.println("Source folder: " + sourceFolder);
                System.out.println("Test folder:   " + testFolder);
                System.out.println("\nMaven Dependencies:");
                System.out.println("  JUnit 5:  " + yn(deps.get("hasJunit5"),  "add junit-jupiter to pom.xml"));
                System.out.println("  Mockito:  " + yn(deps.get("hasMockito"),  "add mockito-core to pom.xml"));
                System.out.println("  Surefire: " + yn(deps.get("hasSurefire"), "add maven-surefire-plugin"));
                System.out.println("  JaCoCo:   " + yn(deps.get("hasJacoco"),   "add jacoco-maven-plugin"));
                System.out.println("\nClasses Found: " + totalClasses);
                System.out.println("  Pending (no tests):   " + pendingCount);
                System.out.println("  With existing tests:  " + existingCount);
                System.out.println("\nClasses with static methods:   " + withStatic);
                System.out.println("Classes with private methods:  " + withPrivate);
                if (pendingCount > 0) {
                    System.out.println("\nRun with --output pending to list classes needing tests.");
                    System.out.println("Run with --output json to get full class details.");
                }
                break;
        }
    }

    static String yn(Object flag, String addMsg) {
        return Boolean.TRUE.equals(flag) ? "Y" : "N  (" + addMsg + ")";
    }

    // -------------------------------------------------------------------------
    // pom.xml inspection
    // -------------------------------------------------------------------------

    static Map<String, Boolean> checkMavenDependencies(Path pomPath) {
        Map<String, Boolean> result = new LinkedHashMap<>();
        result.put("hasPom", true);
        try {
            String content = Files.readString(pomPath, StandardCharsets.UTF_8);
            result.put("hasJunit5",   content.contains("junit-jupiter"));
            result.put("hasMockito",  content.contains("mockito-core") ||
                                      content.contains("mockito-junit-jupiter"));
            result.put("hasSurefire", content.contains("maven-surefire-plugin"));
            result.put("hasJacoco",   content.contains("jacoco-maven-plugin"));
        } catch (IOException e) {
            result.put("hasPom", false);
        }
        return result;
    }

    // -------------------------------------------------------------------------
    // Source folder walker
    // -------------------------------------------------------------------------

    static List<Map<String, Object>> scanSourceFiles(
            String sourceFolder, String testFolder, List<String> exclusions) {

        Path sourcePath = Paths.get(sourceFolder);
        if (!Files.exists(sourcePath)) {
            System.err.println("Error: Source folder does not exist: " + sourceFolder);
            System.exit(1);
        }

        List<Map<String, Object>> classes = new ArrayList<>();
        List<Path> javaFiles = findJavaFiles(sourcePath, exclusions);

        for (Path javaFile : javaFiles) {
            Map<String, Object> info = extractClassInfo(javaFile);
            if (info == null) continue;
            if ("interface".equals(info.get("classType"))) continue;

            // Resolve expected test file
            String pkg      = (String) info.get("package");
            String pkgDir   = pkg.isEmpty() ? "" : pkg.replace(".", File.separator);
            Path   testFile = Paths.get(testFolder, pkgDir,
                              info.get("className") + "Test.java");
            boolean exists  = Files.exists(testFile);

            info.put("testFile",      testFile.toString().replace(File.separatorChar, '/'));
            info.put("testFileExists", exists);
            info.put("status",         exists ? "existing" : "pending");

            classes.add(info);
        }
        return classes;
    }

    static List<Path> findJavaFiles(Path sourcePath, List<String> exclusions) {
        List<Path> javaFiles = new ArrayList<>();
        try {
            Files.walkFileTree(sourcePath, new SimpleFileVisitor<>() {
                @Override
                public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                    if (!file.toString().endsWith(".java")) return FileVisitResult.CONTINUE;
                    String stem = file.getFileName().toString();
                    stem = stem.substring(0, stem.length() - 5);
                    if (stem.equals("package-info") || stem.equals("module-info"))
                        return FileVisitResult.CONTINUE;
                    String relative = sourcePath.relativize(file).toString();
                    if (exclusions.stream().anyMatch(relative::contains))
                        return FileVisitResult.CONTINUE;
                    javaFiles.add(file);
                    return FileVisitResult.CONTINUE;
                }
            });
        } catch (IOException e) {
            System.err.println("Error scanning source folder: " + e.getMessage());
            System.exit(1);
        }
        javaFiles.sort(Comparator.naturalOrder());
        return javaFiles;
    }

    // -------------------------------------------------------------------------
    // Class-level Java parser (regex-based, no external deps)
    // -------------------------------------------------------------------------

    static Map<String, Object> extractClassInfo(Path filePath) {
        String content;
        try {
            content = Files.readString(filePath, StandardCharsets.UTF_8);
        } catch (IOException e) {
            return null;
        }

        // Package
        String pkg = "";
        Matcher pm = Pattern.compile("package\\s+([\\w.]+)\\s*;").matcher(content);
        if (pm.find()) pkg = pm.group(1);

        // Primary type name
        Matcher cm = Pattern.compile(
                "(?:public\\s+)?(?:abstract\\s+)?(?:final\\s+)?" +
                "(?:class|interface|enum|record)\\s+(\\w+)").matcher(content);
        if (!cm.find()) return null;
        String className     = cm.group(1);
        String fullClassName = pkg.isEmpty() ? className : pkg + "." + className;

        // Class type
        String classType = "class";
        if      (Pattern.compile("\\binterface\\s+"  + className).matcher(content).find()) classType = "interface";
        else if (Pattern.compile("\\benum\\s+"       + className).matcher(content).find()) classType = "enum";
        else if (Pattern.compile("\\brecord\\s+"     + className).matcher(content).find()) classType = "record";
        else if (Pattern.compile("\\babstract\\s+class\\s+" + className).matcher(content).find()) classType = "abstract";

        List<Map<String, Object>> methods      = extractMethods(content, className);
        List<Map<String, String>> dependencies = extractDependencies(content);
        boolean hasStatic  = methods.stream().anyMatch(m -> Boolean.TRUE.equals(m.get("isStatic")));
        boolean hasPrivate = methods.stream().anyMatch(m -> "private".equals(m.get("visibility")));

        Map<String, Object> info = new LinkedHashMap<>();
        info.put("filePath",          filePath.toString().replace(File.separatorChar, '/'));
        info.put("package",           pkg);
        info.put("className",         className);
        info.put("fullClassName",     fullClassName);
        info.put("classType",         classType);
        info.put("methods",           methods);
        info.put("dependencies",      dependencies);
        info.put("hasStaticMethods",  hasStatic);
        info.put("hasPrivateMethods", hasPrivate);
        return info;
    }

    static List<Map<String, Object>> extractMethods(String content, String className) {
        List<Map<String, Object>> methods = new ArrayList<>();
        Pattern p = Pattern.compile(
                "(?<vis>public|private|protected)?\\s*" +
                "(?<static>static)?\\s*(?<final>final)?\\s*" +
                "(?<ret>[\\w<>,\\s\\[\\]]+)\\s+(?<name>\\w+)\\s*" +
                "\\((?<params>[^)]*)\\)\\s*(?:throws\\s+(?<throws>[\\w,\\s]+))?\\s*\\{",
                Pattern.MULTILINE);
        Matcher m = p.matcher(content);
        while (m.find()) {
            String name = m.group("name");
            String ret  = m.group("ret") == null ? "" : m.group("ret").trim();
            if (ret.equals(name)) continue; // constructor
            String throwsStr = m.group("throws") == null ? "" : m.group("throws").trim();
            Map<String, Object> method = new LinkedHashMap<>();
            method.put("name",       name);
            method.put("visibility", m.group("vis") != null ? m.group("vis") : "package-private");
            method.put("isStatic",   m.group("static") != null);
            method.put("isFinal",    m.group("final")  != null);
            method.put("returnType", ret);
            method.put("throws",     throwsStr.isEmpty() ? new ArrayList<>() :
                    Arrays.stream(throwsStr.split(","))
                          .map(String::trim).filter(s -> !s.isEmpty())
                          .collect(Collectors.toList()));
            methods.add(method);
        }
        return methods;
    }

    static List<Map<String, String>> extractDependencies(String content) {
        Set<String> skip = Set.of("int","long","double","float","boolean",
                "String","Integer","Long","Double","Float","Boolean","List","Map","Set","Optional");
        List<Map<String, String>> deps = new ArrayList<>();
        Matcher m = Pattern.compile(
                "private\\s+(?:final\\s+)?([\\w]+(?:<[^>]+>)?)\\s+(\\w+)\\s*[;=]")
                .matcher(content);
        while (m.find()) {
            String type = m.group(1), name = m.group(2);
            if (!skip.contains(type) && !skip.contains(capitalize(type)))
                deps.add(Map.of("type", type, "name", name));
        }
        return deps;
    }

    static String capitalize(String s) {
        return s.isEmpty() ? s : Character.toUpperCase(s.charAt(0)) + s.substring(1);
    }

    // -------------------------------------------------------------------------
    // Minimal JSON serializer (no external deps)
    // -------------------------------------------------------------------------

    static String toJson(Object obj) {
        StringBuilder sb = new StringBuilder();
        writeJson(obj, sb, 0);
        return sb.toString();
    }

    @SuppressWarnings("unchecked")
    static void writeJson(Object obj, StringBuilder sb, int indent) {
        String pad = "  ".repeat(indent);
        String pad1 = "  ".repeat(indent + 1);
        if (obj == null) {
            sb.append("null");
        } else if (obj instanceof String) {
            sb.append('"').append(escJson((String) obj)).append('"');
        } else if (obj instanceof Number || obj instanceof Boolean) {
            sb.append(obj);
        } else if (obj instanceof Map) {
            Map<String, Object> map = (Map<String, Object>) obj;
            sb.append("{\n");
            Iterator<Map.Entry<String, Object>> it = map.entrySet().iterator();
            while (it.hasNext()) {
                Map.Entry<String, Object> e = it.next();
                sb.append(pad1).append('"').append(escJson(e.getKey())).append("\": ");
                writeJson(e.getValue(), sb, indent + 1);
                if (it.hasNext()) sb.append(',');
                sb.append('\n');
            }
            sb.append(pad).append('}');
        } else if (obj instanceof List) {
            List<Object> list = (List<Object>) obj;
            if (list.isEmpty()) { sb.append("[]"); return; }
            sb.append("[\n");
            for (int i = 0; i < list.size(); i++) {
                sb.append(pad1);
                writeJson(list.get(i), sb, indent + 1);
                if (i < list.size() - 1) sb.append(',');
                sb.append('\n');
            }
            sb.append(pad).append(']');
        } else {
            sb.append('"').append(escJson(obj.toString())).append('"');
        }
    }

    static String escJson(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t");
    }
}
