#!/usr/bin/env python3
"""Manage .junit-progress.json for the junit-testcase-generator skill.

Works with the skill's canonical per-class schema (status, retryCount, errorHistory).

Usage:
  python3 tracking.py <command> [options]

Commands:
  status                       Print progress summary table
  init                         Create/reset .junit-progress.json from scan JSON
                               (reads scan_project.py --output json from stdin or --scan-file)
  mark <class> <status>        Set a class's status:
                                 pending | in_progress | completed | failed | needs_manual_review
  next [--batch <n>]           Print next N in_progress/pending class names (default: 5)
  reset [--target <t>]         Reset classes back to pending:
                                 all | failed | in_progress  (default: all)
  export                       Print full .junit-progress.json to stdout

Options:
  --project-root <path>        Project root directory (default: .)
  --scan-file <path>           JSON file from scan_project.py (for init)
  --source-folder <path>       Source folder (for init when not in scan output)
  --test-folder <path>         Test folder (for init when not in scan output)
  --batch <n>                  Batch size for next command
  --target <t>                 Reset target
  --reason <text>              Error summary (for mark failed/needs_manual_review)
  --coverage <line%:branch%>   Coverage string to record (e.g. "100%:100%")

Exit codes: 0 = success, 1 = error
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROGRESS_FILE = ".junit-progress.json"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    command     = sys.argv[1]
    project_root = "."
    scan_file   = None
    source_folder = "src/main/java"
    test_folder   = "src/test/java"
    batch_size  = 5
    reset_target = "all"
    reason      = ""
    coverage    = ""

    # Positional args for 'mark': class name and status follow command directly
    mark_class_name = None
    mark_status     = None

    raw_args = sys.argv[2:]
    i = 0
    positional = []
    while i < len(raw_args):
        a = raw_args[i]
        if   a == "--project-root":  project_root  = raw_args[i + 1]; i += 2
        elif a == "--scan-file":     scan_file     = raw_args[i + 1]; i += 2
        elif a == "--source-folder": source_folder = raw_args[i + 1]; i += 2
        elif a == "--test-folder":   test_folder   = raw_args[i + 1]; i += 2
        elif a == "--batch":         batch_size    = int(raw_args[i + 1]); i += 2
        elif a == "--target":        reset_target  = raw_args[i + 1]; i += 2
        elif a == "--reason":        reason        = raw_args[i + 1]; i += 2
        elif a == "--coverage":      coverage      = raw_args[i + 1]; i += 2
        elif not a.startswith("--"): positional.append(a); i += 1
        else: i += 1

    if command == "mark":
        if len(positional) < 2:
            print("Usage: tracking.py mark <class_name> <status> [--reason <text>]",
                  file=sys.stderr)
            sys.exit(1)
        mark_class_name = positional[0]
        mark_status     = positional[1]

    progress_path = Path(project_root) / PROGRESS_FILE

    if   command == "status": show_status(progress_path)
    elif command == "init":   init_progress(progress_path, project_root,
                                            source_folder, test_folder, scan_file)
    elif command == "mark":   mark_class(progress_path, mark_class_name,
                                         mark_status, reason, coverage)
    elif command == "next":   next_batch(progress_path, batch_size)
    elif command == "reset":  reset_progress(progress_path, reset_target)
    elif command == "export":
        if progress_path.exists():
            print(progress_path.read_text(encoding="utf-8"))
        else:
            print("{}", file=sys.stderr); sys.exit(1)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def load_progress(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_progress(path: Path, data: dict):
    data["lastUpdatedAt"] = datetime.now(timezone.utc).isoformat()
    try:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as e:
        print(f"Warning: Could not save {path}: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def show_status(progress_path: Path):
    data = load_progress(progress_path)
    if not data:
        print(f"No {PROGRESS_FILE} found. Run 'tracking.py init' first.")
        return

    files = data.get("files", {})
    icons = {
        "completed":           "✅",
        "in_progress":         "🔄",
        "pending":             "⏳",
        "failed":              "❌",
        "needs_manual_review": "⚠️ ",
    }

    print(f"\nProject: {data.get('projectRoot', '.')}")
    print(f"Scanned: {data.get('scannedAt', 'N/A')}")
    print(f"Updated: {data.get('lastUpdatedAt', 'N/A')}")

    if not files:
        print("\nNo classes tracked yet.")
        return

    col = max((len(k) for k in files), default=40)
    col = max(col, 40)
    print()
    print(f"{'Class':<{col}}  {'Status':<24}  {'Ret':>3}  {'Line%':>6}  {'Branch%':>7}  Last Error")
    print("-" * (col + 60))

    counts: dict[str, int] = {}
    for class_name, info in files.items():
        status  = info.get("status", "pending")
        counts[status] = counts.get(status, 0) + 1
        icon    = icons.get(status, "  ")
        retries = info.get("retryCount", 0)
        line_cov   = info.get("lineCoverage",   "—")
        branch_cov = info.get("branchCoverage", "—")
        history = info.get("errorHistory", [])
        last_err = (history[-1].get("errorSummary", "")[:38] + "…"
                    if history and len(history[-1].get("errorSummary", "")) > 38
                    else history[-1].get("errorSummary", "—") if history else "—")
        print(f"{class_name:<{col}}  {icon} {status:<22}  {retries:>3}  {line_cov:>6}  {branch_cov:>7}  {last_err}")

    print()
    parts = [f"{v} {k}" for k, v in counts.items() if v > 0]
    print("Summary: " + " | ".join(parts))
    total = len(files)
    done  = counts.get("completed", 0)
    if total:
        print(f"Progress: {done}/{total} ({done * 100 // total}%)")


def init_progress(progress_path: Path, project_root: str,
                  source_folder: str, test_folder: str, scan_file: str | None):
    """Initialise .junit-progress.json from scan_project.py JSON output."""
    if scan_file:
        raw = Path(scan_file).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    scan_data = json.loads(raw)

    # Preserve already-completed entries from an existing progress file
    existing       = load_progress(progress_path)
    existing_files = existing.get("files", {})

    files: dict[str, dict] = {}
    for cls in scan_data.get("classes", []):
        fqn = cls["fullClassName"]
        # Keep completed entries intact
        if fqn in existing_files and existing_files[fqn].get("status") == "completed":
            files[fqn] = existing_files[fqn]
            continue
        # Treat classes that already have a test file as completed stubs
        initial_status = "completed" if cls.get("testFileExists") else "pending"
        files[fqn] = {
            "sourceFile":    cls.get("filePath", ""),
            "testFile":      cls.get("testFile",  ""),
            "status":        initial_status,
            "retryCount":    0,
            "errorHistory":  [],
            "startedAt":     None,
            "completedAt":   None,
        }

    data = {
        "projectRoot":  project_root,
        "sourceFolder": scan_data.get("sourceFolder", source_folder),
        "testFolder":   scan_data.get("testFolder",   test_folder),
        "scannedAt":    scan_data.get("scannedAt",    datetime.now(timezone.utc).isoformat()),
        "files":        files,
    }
    save_progress(progress_path, data)

    total   = len(files)
    pending = sum(1 for f in files.values() if f["status"] == "pending")
    done    = sum(1 for f in files.values() if f["status"] == "completed")
    print(f"Initialized {PROGRESS_FILE}: {total} classes, {pending} pending, {done} with existing tests.")


def mark_class(progress_path: Path, class_name: str, status: str,
               reason: str = "", coverage: str = ""):
    data = load_progress(progress_path)
    if not data:
        print(f"Error: {PROGRESS_FILE} not found. Run 'tracking.py init' first.",
              file=sys.stderr)
        sys.exit(1)

    files = data.get("files", {})

    # Exact match first, then suffix/substring match
    if class_name in files:
        match_key = class_name
    else:
        candidates = [k for k in files if k.endswith(class_name) or class_name in k]
        if len(candidates) == 1:
            match_key = candidates[0]
        elif len(candidates) > 1:
            print(f"Ambiguous class name '{class_name}'. Matches: {candidates}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Class '{class_name}' not found in {PROGRESS_FILE}.", file=sys.stderr)
            sys.exit(1)

    entry     = files[match_key]
    old_status = entry.get("status", "pending")
    entry["status"] = status
    now = datetime.now(timezone.utc).isoformat()

    if status == "in_progress" and not entry.get("startedAt"):
        entry["startedAt"] = now
    elif status == "completed":
        entry["completedAt"] = now
        if coverage:
            parts = coverage.split(":")
            entry["lineCoverage"]   = parts[0] if len(parts) > 0 else ""
            entry["branchCoverage"] = parts[1] if len(parts) > 1 else ""
    elif status in ("failed", "needs_manual_review") and reason:
        entry["retryCount"] = entry.get("retryCount", 0) + 1
        entry.setdefault("errorHistory", []).append({
            "attempt":      entry["retryCount"],
            "timestamp":    now,
            "errorSummary": reason[:500],
        })

    save_progress(progress_path, data)
    print(f"Marked {match_key}: {old_status} → {status}")


def next_batch(progress_path: Path, batch_size: int):
    """Print the next in_progress then pending class names as a JSON array."""
    data  = load_progress(progress_path)
    files = data.get("files", {})
    # in_progress first (resume interrupted work), then pending
    result = [k for k, v in files.items() if v.get("status") == "in_progress"]
    result += [k for k, v in files.items() if v.get("status") == "pending"]
    print(json.dumps(result[:batch_size], indent=2))


def reset_progress(progress_path: Path, target: str):
    data = load_progress(progress_path)
    if not data:
        print("No tracking file to reset.")
        return

    files = data.get("files", {})
    count = 0
    for info in files.values():
        status = info.get("status", "pending")
        should_reset = (
            target == "all"
            or (target == "failed"      and status in ("failed", "needs_manual_review"))
            or (target == "in_progress" and status == "in_progress")
        )
        if should_reset:
            info.update({
                "status":       "pending",
                "retryCount":   0,
                "errorHistory": [],
                "startedAt":    None,
                "completedAt":  None,
            })
            count += 1

    save_progress(progress_path, data)
    print(f"Reset {count} class(es) to pending (target: {target})")


if __name__ == "__main__":
    main()
