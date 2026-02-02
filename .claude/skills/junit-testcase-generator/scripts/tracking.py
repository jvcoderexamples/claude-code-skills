#!/usr/bin/env python3
"""
Manage test generation tracking file.
Supports status checks, manual updates, and reset operations.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

TRACKING_FILE = ".junit-generator-tracking.json"


def load_tracking(project_root: str) -> Optional[Dict]:
    """Load tracking data from file."""
    tracking_path = Path(project_root) / TRACKING_FILE
    if not tracking_path.exists():
        return None

    with open(tracking_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_tracking(project_root: str, tracking: Dict) -> None:
    """Save tracking data to file."""
    tracking_path = Path(project_root) / TRACKING_FILE
    tracking["lastUpdated"] = datetime.now().isoformat()

    with open(tracking_path, 'w', encoding='utf-8') as f:
        json.dump(tracking, f, indent=2)


def init_tracking(project_root: str) -> Dict:
    """Initialize a new tracking file."""
    tracking = {
        "generated": [],
        "pending": [],
        "failed": {},
        "lastRun": None,
        "lastUpdated": datetime.now().isoformat(),
        "projectRoot": project_root
    }
    save_tracking(project_root, tracking)
    return tracking


def show_status(project_root: str) -> None:
    """Display tracking status."""
    tracking = load_tracking(project_root)

    if not tracking:
        print(f"No tracking file found at {project_root}/{TRACKING_FILE}")
        print("Run 'scan_project.py' first to initialize tracking.")
        return

    print(f"\n=== JUnit Generator Tracking Status ===")
    print(f"Project: {tracking.get('projectRoot', 'N/A')}")
    print(f"Last run: {tracking.get('lastRun', 'Never')}")
    print(f"Last updated: {tracking.get('lastUpdated', 'N/A')}")

    generated = tracking.get('generated', [])
    pending = tracking.get('pending', [])
    failed = tracking.get('failed', {})

    print(f"\nProgress:")
    print(f"  Generated: {len(generated)}")
    print(f"  Pending:   {len(pending)}")
    print(f"  Failed:    {len(failed)}")

    total = len(generated) + len(pending) + len(failed)
    if total > 0:
        pct = (len(generated) / total) * 100
        print(f"  Progress:  {pct:.1f}%")

    if pending:
        print(f"\nNext classes to generate (first 10):")
        for cls in pending[:10]:
            print(f"  - {cls}")
        if len(pending) > 10:
            print(f"  ... and {len(pending) - 10} more")

    if failed:
        print(f"\nFailed classes:")
        for cls, reason in list(failed.items())[:5]:
            print(f"  - {cls}: {reason[:60]}")


def mark_generated(project_root: str, class_names: List[str]) -> None:
    """Mark classes as having tests generated."""
    tracking = load_tracking(project_root)
    if not tracking:
        tracking = init_tracking(project_root)

    for cls in class_names:
        if cls not in tracking["generated"]:
            tracking["generated"].append(cls)

        if cls in tracking["pending"]:
            tracking["pending"].remove(cls)

        if cls in tracking.get("failed", {}):
            del tracking["failed"][cls]

    save_tracking(project_root, tracking)
    print(f"Marked {len(class_names)} class(es) as generated")


def mark_failed(project_root: str, class_name: str, reason: str) -> None:
    """Mark a class as failed."""
    tracking = load_tracking(project_root)
    if not tracking:
        tracking = init_tracking(project_root)

    tracking["failed"][class_name] = reason

    if class_name in tracking["pending"]:
        tracking["pending"].remove(class_name)

    save_tracking(project_root, tracking)
    print(f"Marked {class_name} as failed: {reason}")


def mark_pending(project_root: str, class_names: List[str]) -> None:
    """Mark classes as pending (needing tests)."""
    tracking = load_tracking(project_root)
    if not tracking:
        tracking = init_tracking(project_root)

    for cls in class_names:
        if cls not in tracking["pending"] and cls not in tracking["generated"]:
            tracking["pending"].append(cls)

        # Remove from failed if present
        if cls in tracking.get("failed", {}):
            del tracking["failed"][cls]

    save_tracking(project_root, tracking)
    print(f"Added {len(class_names)} class(es) to pending")


def reset_tracking(project_root: str, what: str = "all") -> None:
    """Reset tracking data."""
    tracking = load_tracking(project_root)
    if not tracking:
        print("No tracking file to reset")
        return

    if what == "all":
        tracking = init_tracking(project_root)
        print("Reset all tracking data")
    elif what == "failed":
        # Move failed back to pending
        failed = tracking.get("failed", {})
        tracking["pending"].extend(failed.keys())
        tracking["failed"] = {}
        save_tracking(project_root, tracking)
        print(f"Reset {len(failed)} failed classes to pending")
    elif what == "pending":
        tracking["pending"] = []
        save_tracking(project_root, tracking)
        print("Cleared pending list")
    else:
        print(f"Unknown reset target: {what}")


def get_next_batch(project_root: str, batch_size: int = 5) -> List[str]:
    """Get next batch of classes to process."""
    tracking = load_tracking(project_root)
    if not tracking:
        return []

    pending = tracking.get("pending", [])
    return pending[:batch_size]


def export_report(project_root: str, output_file: str = None) -> None:
    """Export tracking data as report."""
    tracking = load_tracking(project_root)
    if not tracking:
        print("No tracking data to export")
        return

    report = {
        "generatedAt": datetime.now().isoformat(),
        "summary": {
            "generated": len(tracking.get("generated", [])),
            "pending": len(tracking.get("pending", [])),
            "failed": len(tracking.get("failed", {}))
        },
        "generatedClasses": tracking.get("generated", []),
        "pendingClasses": tracking.get("pending", []),
        "failedClasses": tracking.get("failed", {})
    }

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"Report exported to {output_file}")
    else:
        print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Manage JUnit test generation tracking"
    )
    parser.add_argument(
        "command",
        choices=["status", "mark-generated", "mark-failed", "mark-pending",
                 "reset", "next-batch", "export"],
        help="Command to execute"
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root directory"
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        help="Class names (for mark commands)"
    )
    parser.add_argument(
        "--reason",
        help="Failure reason (for mark-failed)"
    )
    parser.add_argument(
        "--reset-target",
        choices=["all", "failed", "pending"],
        default="all",
        help="What to reset"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Batch size for next-batch command"
    )
    parser.add_argument(
        "--output",
        help="Output file for export"
    )

    args = parser.parse_args()

    if args.command == "status":
        show_status(args.project_root)

    elif args.command == "mark-generated":
        if not args.classes:
            print("Error: --classes required for mark-generated")
            sys.exit(1)
        mark_generated(args.project_root, args.classes)

    elif args.command == "mark-failed":
        if not args.classes or len(args.classes) != 1:
            print("Error: exactly one class required for mark-failed")
            sys.exit(1)
        reason = args.reason or "Unknown error"
        mark_failed(args.project_root, args.classes[0], reason)

    elif args.command == "mark-pending":
        if not args.classes:
            print("Error: --classes required for mark-pending")
            sys.exit(1)
        mark_pending(args.project_root, args.classes)

    elif args.command == "reset":
        reset_tracking(args.project_root, args.reset_target)

    elif args.command == "next-batch":
        batch = get_next_batch(args.project_root, args.batch_size)
        if batch:
            print(json.dumps(batch))
        else:
            print("[]")

    elif args.command == "export":
        export_report(args.project_root, args.output)


if __name__ == "__main__":
    main()
