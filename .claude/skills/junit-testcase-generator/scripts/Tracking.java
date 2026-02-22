import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Manage .junit-progress.json for the junit-testcase-generator skill.
 *
 * Works with the skill's canonical per-class schema.
 * Equivalent to tracking.py.
 *
 * Usage: java --source 11 Tracking.java <command> [options]
 *
 * Commands:
 *   status                       Print progress summary table
 *   init                         Create/reset .junit-progress.json from scan JSON (stdin or --scan-file)
 *   mark <class> <status>        Set a class's status:
 *                                  pending|in_progress|completed|failed|needs_manual_review
 *   next [--batch <n>]           Print next N in_progress/pending class names (default: 5)
 *   reset [--target <t>]         Reset classes to pending: all|failed|in_progress (default: all)
 *   export                       Print full .junit-progress.json to stdout
 *
 * Options:
 *   --project-root <path>        Project root (default: .)
 *   --scan-file <path>           JSON file from ScanProject.java --output json (for init)
 *   --source-folder <path>       Source folder (for init)
 *   --test-folder <path>         Test folder (for init)
 *   --batch <n>                  Batch size for next command
 *   --target <t>                 Reset target
 *   --reason <text>              Error summary (for mark failed/needs_manual_review)
 *   --coverage <line%:branch%>   Coverage string to record (for mark completed)
 */
public class Tracking {

    static final String PROGRESS_FILE = ".junit-progress.json";

    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            System.err.println("Usage: java --source 11 Tracking.java <command> [options]");
            System.exit(1);
        }

        String command      = args[0];
        String projectRoot  = ".";
        String scanFile     = null;
        String sourceFolder = "src/main/java";
        String testFolder   = "src/test/java";
        int    batchSize    = 5;
        String resetTarget  = "all";
        String reason       = "";
        String coverage     = "";
        List<String> positional = new ArrayList<>();

        for (int i = 1; i < args.length; i++) {
            switch (args[i]) {
                case "--project-root":  projectRoot  = args[++i]; break;
                case "--scan-file":     scanFile     = args[++i]; break;
                case "--source-folder": sourceFolder = args[++i]; break;
                case "--test-folder":   testFolder   = args[++i]; break;
                case "--batch":         batchSize    = Integer.parseInt(args[++i]); break;
                case "--target":        resetTarget  = args[++i]; break;
                case "--reason":        reason       = args[++i]; break;
                case "--coverage":      coverage     = args[++i]; break;
                default:
                    if (!args[i].startsWith("--")) positional.add(args[i]);
                    break;
            }
        }

        Path progressPath = Paths.get(projectRoot, PROGRESS_FILE);

        switch (command) {
            case "status": showStatus(progressPath); break;
            case "init":   initProgress(progressPath, projectRoot, sourceFolder,
                                        testFolder, scanFile); break;
            case "mark":
                if (positional.size() < 2) {
                    System.err.println("Usage: Tracking.java mark <class_name> <status> [--reason <text>]");
                    System.exit(1);
                }
                markClass(progressPath, positional.get(0), positional.get(1), reason, coverage);
                break;
            case "next":   nextBatch(progressPath, batchSize); break;
            case "reset":  resetProgress(progressPath, resetTarget); break;
            case "export":
                if (Files.exists(progressPath)) {
                    System.out.println(Files.readString(progressPath, StandardCharsets.UTF_8));
                } else {
                    System.err.println("No " + PROGRESS_FILE + " found.");
                    System.exit(1);
                }
                break;
            default:
                System.err.println("Unknown command: " + command);
                System.exit(1);
        }
    }

    // -------------------------------------------------------------------------
    // File I/O
    // -------------------------------------------------------------------------

    @SuppressWarnings("unchecked")
    static Map<String, Object> loadProgress(Path path) {
        if (!Files.exists(path)) return new LinkedHashMap<>();
        try {
            return parseJsonObject(Files.readString(path, StandardCharsets.UTF_8));
        } catch (IOException e) {
            return new LinkedHashMap<>();
        }
    }

    static void saveProgress(Path path, Map<String, Object> data) {
        data.put("lastUpdatedAt", Instant.now().toString());
        try {
            Files.writeString(path, toJson(data), StandardCharsets.UTF_8);
        } catch (IOException e) {
            System.err.println("Warning: Could not save " + path + ": " + e.getMessage());
        }
    }

    // -------------------------------------------------------------------------
    // Commands
    // -------------------------------------------------------------------------

    @SuppressWarnings("unchecked")
    static void showStatus(Path progressPath) {
        Map<String, Object> data = loadProgress(progressPath);
        if (data.isEmpty()) {
            System.out.println("No " + PROGRESS_FILE + " found. Run 'Tracking.java init' first.");
            return;
        }

        System.out.println("\nProject: " + data.getOrDefault("projectRoot", "."));
        System.out.println("Scanned: " + data.getOrDefault("scannedAt", "N/A"));
        System.out.println("Updated: " + data.getOrDefault("lastUpdatedAt", "N/A"));

        Map<String, Object> files = (Map<String, Object>) data.getOrDefault("files", new LinkedHashMap<>());
        if (files.isEmpty()) { System.out.println("\nNo classes tracked yet."); return; }

        int col = files.keySet().stream().mapToInt(String::length).max().orElse(40);
        col = Math.max(col, 40);

        System.out.println();
        System.out.printf("%-" + col + "s  %-24s  %3s  %6s  %7s  %s%n",
                "Class", "Status", "Ret", "Line%", "Branch%", "Last Error");
        System.out.println("-".repeat(col + 62));

        Map<String, Integer> counts = new LinkedHashMap<>();
        for (Map.Entry<String, Object> e : files.entrySet()) {
            Map<String, Object> info = (Map<String, Object>) e.getValue();
            String status   = (String) info.getOrDefault("status", "pending");
            String icon     = statusIcon(status);
            int    retries  = ((Number) info.getOrDefault("retryCount", 0)).intValue();
            String lineCov  = (String) info.getOrDefault("lineCoverage",   "—");
            String brnCov   = (String) info.getOrDefault("branchCoverage", "—");
            List<Object> history = (List<Object>) info.getOrDefault("errorHistory", new ArrayList<>());
            String lastErr = history.isEmpty() ? "—" :
                    truncate((String) ((Map<?,?>) history.get(history.size()-1))
                            .getOrDefault("errorSummary", ""), 38);

            System.out.printf("%-" + col + "s  %s%-" + (24 - icon.length()) + "s  %3d  %6s  %7s  %s%n",
                    e.getKey(), icon, status, retries, lineCov, brnCov, lastErr);
            counts.merge(status, 1, Integer::sum);
        }

        System.out.println();
        System.out.println("Summary: " + counts.entrySet().stream()
                .map(e -> e.getValue() + " " + e.getKey()).collect(Collectors.joining(" | ")));
        int total = files.size();
        int done  = counts.getOrDefault("completed", 0);
        if (total > 0) System.out.printf("Progress: %d/%d (%d%%)%n", done, total, done * 100 / total);
    }

    static String statusIcon(String status) {
        switch (status) {
            case "completed":           return "✅";
            case "in_progress":         return "🔄";
            case "pending":             return "⏳";
            case "failed":              return "❌";
            case "needs_manual_review": return "⚠️ ";
            default: return "  ";
        }
    }

    @SuppressWarnings("unchecked")
    static void initProgress(Path progressPath, String projectRoot,
                             String sourceFolder, String testFolder,
                             String scanFile) throws Exception {
        String raw;
        if (scanFile != null) {
            raw = Files.readString(Paths.get(scanFile), StandardCharsets.UTF_8);
        } else {
            raw = new String(System.in.readAllBytes(), StandardCharsets.UTF_8);
        }

        Map<String, Object> scanData = parseJsonObject(raw);
        Map<String, Object> existing = loadProgress(progressPath);
        Map<String, Object> existingFiles =
                (Map<String, Object>) existing.getOrDefault("files", new LinkedHashMap<>());

        List<Object> classList = (List<Object>) scanData.getOrDefault("classes", new ArrayList<>());
        Map<String, Object> files = new LinkedHashMap<>();

        for (Object obj : classList) {
            Map<String, Object> cls = (Map<String, Object>) obj;
            String fqn = (String) cls.get("fullClassName");

            // Keep completed entries intact
            if (existingFiles.containsKey(fqn) &&
                    "completed".equals(((Map<?,?>) existingFiles.get(fqn)).get("status"))) {
                files.put(fqn, existingFiles.get(fqn));
                continue;
            }

            boolean hasTest     = Boolean.TRUE.equals(cls.get("testFileExists"));
            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("sourceFile",   cls.getOrDefault("filePath",  ""));
            entry.put("testFile",     cls.getOrDefault("testFile",   ""));
            entry.put("status",       hasTest ? "completed" : "pending");
            entry.put("retryCount",   0);
            entry.put("errorHistory", new ArrayList<>());
            entry.put("startedAt",    null);
            entry.put("completedAt",  null);
            files.put(fqn, entry);
        }

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("projectRoot",  projectRoot);
        data.put("sourceFolder", scanData.getOrDefault("sourceFolder", sourceFolder));
        data.put("testFolder",   scanData.getOrDefault("testFolder",   testFolder));
        data.put("scannedAt",    scanData.getOrDefault("scannedAt",    Instant.now().toString()));
        data.put("files",        files);
        saveProgress(progressPath, data);

        long total   = files.size();
        long pending = files.values().stream().filter(v ->
                "pending".equals(((Map<?,?>) v).get("status"))).count();
        long done    = files.values().stream().filter(v ->
                "completed".equals(((Map<?,?>) v).get("status"))).count();
        System.out.println("Initialized " + PROGRESS_FILE + ": " + total +
                " classes, " + pending + " pending, " + done + " with existing tests.");
    }

    @SuppressWarnings("unchecked")
    static void markClass(Path progressPath, String className, String status,
                          String reason, String coverage) {
        Map<String, Object> data = loadProgress(progressPath);
        if (data.isEmpty()) {
            System.err.println("Error: " + PROGRESS_FILE + " not found. Run 'init' first.");
            System.exit(1);
        }

        Map<String, Object> files = (Map<String, Object>) data.getOrDefault("files", new LinkedHashMap<>());

        // Exact match first, then suffix/substring
        String matchKey = null;
        if (files.containsKey(className)) {
            matchKey = className;
        } else {
            List<String> candidates = files.keySet().stream()
                    .filter(k -> k.endsWith(className) || k.contains(className))
                    .collect(Collectors.toList());
            if (candidates.size() == 1) matchKey = candidates.get(0);
            else if (candidates.size() > 1) {
                System.err.println("Ambiguous class name '" + className + "'. Matches: " + candidates);
                System.exit(1);
            }
        }

        if (matchKey == null) {
            System.err.println("Class '" + className + "' not found in " + PROGRESS_FILE + ".");
            System.exit(1);
        }

        Map<String, Object> entry   = (Map<String, Object>) files.get(matchKey);
        String oldStatus = (String) entry.getOrDefault("status", "pending");
        entry.put("status", status);
        String now = Instant.now().toString();

        if ("in_progress".equals(status) && entry.get("startedAt") == null) {
            entry.put("startedAt", now);
        } else if ("completed".equals(status)) {
            entry.put("completedAt", now);
            if (!coverage.isEmpty()) {
                String[] parts = coverage.split(":");
                entry.put("lineCoverage",   parts.length > 0 ? parts[0] : "");
                entry.put("branchCoverage", parts.length > 1 ? parts[1] : "");
            }
        } else if (("failed".equals(status) || "needs_manual_review".equals(status))
                && !reason.isEmpty()) {
            int retries = ((Number) entry.getOrDefault("retryCount", 0)).intValue() + 1;
            entry.put("retryCount", retries);
            List<Object> history = new ArrayList<>((List<Object>) entry.getOrDefault("errorHistory", new ArrayList<>()));
            Map<String, Object> err = new LinkedHashMap<>();
            err.put("attempt",      retries);
            err.put("timestamp",    now);
            err.put("errorSummary", reason.length() > 500 ? reason.substring(0, 500) : reason);
            history.add(err);
            entry.put("errorHistory", history);
        }

        saveProgress(progressPath, data);
        System.out.println("Marked " + matchKey + ": " + oldStatus + " → " + status);
    }

    @SuppressWarnings("unchecked")
    static void nextBatch(Path progressPath, int batchSize) {
        Map<String, Object> data  = loadProgress(progressPath);
        Map<String, Object> files = (Map<String, Object>) data.getOrDefault("files", new LinkedHashMap<>());

        List<String> result = new ArrayList<>();
        // in_progress first (resume interrupted work), then pending
        files.entrySet().stream()
                .filter(e -> "in_progress".equals(((Map<?,?>) e.getValue()).get("status")))
                .map(Map.Entry::getKey).forEach(result::add);
        files.entrySet().stream()
                .filter(e -> "pending".equals(((Map<?,?>) e.getValue()).get("status")))
                .map(Map.Entry::getKey).forEach(result::add);

        List<String> batch = result.stream().limit(batchSize).collect(Collectors.toList());
        System.out.println(toJsonStringArray(batch));
    }

    @SuppressWarnings("unchecked")
    static void resetProgress(Path progressPath, String target) {
        Map<String, Object> data = loadProgress(progressPath);
        if (data.isEmpty()) { System.out.println("No tracking file to reset."); return; }

        Map<String, Object> files = (Map<String, Object>) data.getOrDefault("files", new LinkedHashMap<>());
        int count = 0;
        for (Map<String, Object> info : files.values().stream()
                .map(v -> (Map<String, Object>) v).collect(Collectors.toList())) {
            String status = (String) info.getOrDefault("status", "pending");
            boolean reset = "all".equals(target)
                    || ("failed".equals(target)      && (status.equals("failed") || status.equals("needs_manual_review")))
                    || ("in_progress".equals(target) && status.equals("in_progress"));
            if (reset) {
                info.put("status",       "pending");
                info.put("retryCount",   0);
                info.put("errorHistory", new ArrayList<>());
                info.put("startedAt",    null);
                info.put("completedAt",  null);
                count++;
            }
        }

        saveProgress(progressPath, data);
        System.out.println("Reset " + count + " class(es) to pending (target: " + target + ")");
    }

    // -------------------------------------------------------------------------
    // Minimal JSON serializer + parser (no external deps)
    // -------------------------------------------------------------------------

    static String toJson(Object obj) {
        StringBuilder sb = new StringBuilder();
        writeJson(obj, sb, 0);
        return sb.toString();
    }

    static String toJsonStringArray(List<String> list) {
        if (list.isEmpty()) return "[]";
        return list.stream().map(s -> "\"" + escJson(s) + "\"")
                .collect(Collectors.joining(", ", "[", "]"));
    }

    @SuppressWarnings("unchecked")
    static void writeJson(Object obj, StringBuilder sb, int indent) {
        String pad  = "  ".repeat(indent);
        String pad1 = "  ".repeat(indent + 1);
        if (obj == null) { sb.append("null"); }
        else if (obj instanceof String)  { sb.append('"').append(escJson((String) obj)).append('"'); }
        else if (obj instanceof Number || obj instanceof Boolean) { sb.append(obj); }
        else if (obj instanceof Map) {
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
                sb.append(pad1); writeJson(list.get(i), sb, indent + 1);
                if (i < list.size() - 1) sb.append(',');
                sb.append('\n');
            }
            sb.append(pad).append(']');
        } else { sb.append('"').append(escJson(obj.toString())).append('"'); }
    }

    static String escJson(String s) {
        return s.replace("\\","\\\\").replace("\"","\\\"")
                .replace("\n","\\n").replace("\r","\\r").replace("\t","\\t");
    }

    static String truncate(String s, int max) {
        if (s == null) return "";
        return s.length() <= max ? s : s.substring(0, max) + "…";
    }

    // --- Minimal JSON parser ---

    static Map<String, Object> parseJsonObject(String json) {
        int[] pos = {0};
        skipWs(json, pos);
        if (pos[0] < json.length() && json.charAt(pos[0]) == '{')
            return (Map<String, Object>) parseVal(json, pos);
        return new LinkedHashMap<>();
    }

    @SuppressWarnings("unchecked")
    static Object parseVal(String json, int[] pos) {
        skipWs(json, pos);
        if (pos[0] >= json.length()) return null;
        char c = json.charAt(pos[0]);
        if (c == '"') return parseStr(json, pos);
        if (c == '{') {
            pos[0]++;
            Map<String, Object> obj = new LinkedHashMap<>();
            skipWs(json, pos);
            if (pos[0] < json.length() && json.charAt(pos[0]) == '}') { pos[0]++; return obj; }
            while (pos[0] < json.length()) {
                skipWs(json, pos);
                String key = parseStr(json, pos); skipWs(json, pos);
                if (pos[0] < json.length() && json.charAt(pos[0]) == ':') pos[0]++;
                skipWs(json, pos);
                obj.put(key, parseVal(json, pos)); skipWs(json, pos);
                if (pos[0] < json.length() && json.charAt(pos[0]) == ',') pos[0]++;
                else break;
            }
            if (pos[0] < json.length() && json.charAt(pos[0]) == '}') pos[0]++;
            return obj;
        }
        if (c == '[') {
            pos[0]++;
            List<Object> list = new ArrayList<>();
            skipWs(json, pos);
            if (pos[0] < json.length() && json.charAt(pos[0]) == ']') { pos[0]++; return list; }
            while (pos[0] < json.length()) {
                skipWs(json, pos); list.add(parseVal(json, pos)); skipWs(json, pos);
                if (pos[0] < json.length() && json.charAt(pos[0]) == ',') pos[0]++;
                else break;
            }
            if (pos[0] < json.length() && json.charAt(pos[0]) == ']') pos[0]++;
            return list;
        }
        if (json.startsWith("null",  pos[0])) { pos[0] += 4; return null; }
        if (json.startsWith("true",  pos[0])) { pos[0] += 4; return true; }
        if (json.startsWith("false", pos[0])) { pos[0] += 5; return false; }
        int start = pos[0];
        while (pos[0] < json.length() && "0123456789.-+eE".indexOf(json.charAt(pos[0])) >= 0) pos[0]++;
        String num = json.substring(start, pos[0]);
        try { return num.contains(".") ? Double.parseDouble(num) : Long.parseLong(num); }
        catch (NumberFormatException e) { return num; }
    }

    static String parseStr(String json, int[] pos) {
        if (pos[0] >= json.length() || json.charAt(pos[0]) != '"') return "";
        pos[0]++;
        StringBuilder sb = new StringBuilder();
        while (pos[0] < json.length()) {
            char c = json.charAt(pos[0]);
            if (c == '\\' && pos[0] + 1 < json.length()) {
                char n = json.charAt(pos[0] + 1);
                switch (n) { case '"': sb.append('"'); break; case '\\': sb.append('\\'); break;
                    case 'n': sb.append('\n'); break; case 'r': sb.append('\r'); break;
                    case 't': sb.append('\t'); break; default: sb.append(n); }
                pos[0] += 2;
            } else if (c == '"') { pos[0]++; return sb.toString(); }
            else { sb.append(c); pos[0]++; }
        }
        return sb.toString();
    }

    static void skipWs(String json, int[] pos) {
        while (pos[0] < json.length() && Character.isWhitespace(json.charAt(pos[0]))) pos[0]++;
    }
}
