#!/usr/bin/env python3
"""
Batch processing manager for review training data extraction.

Provides stateful batch processing of matched review/source pairs:
- Pops one matched pair at a time from matched directory
- Tracks processing state for resume capability
- Deletes source pair only after explicit confirmation
- Logs all processing decisions

Usage:
    # Get next matched pair to process
    python batch_next.py next

    # Confirm processing complete (deletes source pair)
    python batch_next.py confirm <pair_dir_name>

    # Mark pair as failed (moves to failed directory)
    python batch_next.py fail <pair_dir_name> <reason>

    # Get processing status
    python batch_next.py status

    # Reset state (DANGEROUS - use only for testing)
    python batch_next.py reset
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Paths
ARCHIVE_ROOT = Path("/home/nic/src/writing-archive/archive")
MATCHED_DIR = ARCHIVE_ROOT / "matched"
PROCESSED_DIR = ARCHIVE_ROOT / "processed_pairs"
FAILED_DIR = ARCHIVE_ROOT / "failed_extraction"
STATE_FILE = ARCHIVE_ROOT / "review_processing_state.json"
LOG_FILE = ARCHIVE_ROOT / "review_processing.log"


class ReviewBatchProcessor:
    """Manages stateful batch processing of matched review/source pairs."""

    def __init__(self) -> None:
        """Initialize batch processor, ensuring required directories exist."""
        MATCHED_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        FAILED_DIR.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load processing state from disk."""
        if STATE_FILE.exists():
            with STATE_FILE.open("r") as f:
                return json.load(f)
        return {
            "current_pair": None,
            "processed_count": 0,
            "failed_count": 0,
            "started_at": None,
            "last_updated": None,
        }

    def _save_state(self) -> None:
        """Save processing state to disk."""
        self.state["last_updated"] = datetime.now().isoformat()
        with STATE_FILE.open("w") as f:
            json.dump(self.state, f, indent=2)

    def _log(self, pair_name: str, decision: str, reason: str) -> None:
        """Append entry to processing log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} | {pair_name} | {decision} | {reason}\n"
        with LOG_FILE.open("a") as f:
            f.write(log_entry)

    def get_next(self) -> dict | None:
        """
        Get next matched pair to process.

        Returns:
            dict with 'pair_dir', 'pair_name', 'review_path', 'source_path', 'metadata_path'
            or None if no pairs remaining
        """
        # Check if there's a current pair in progress
        if self.state["current_pair"]:
            current_path = Path(self.state["current_pair"])
            if current_path.exists():
                print(
                    f"WARNING: Current pair still in progress: {current_path.name}",
                    file=sys.stderr,
                )
                print(
                    "Use 'confirm' or 'fail' to complete before getting next pair",
                    file=sys.stderr,
                )
                return None

        # Get list of matched pair directories
        pairs = sorted([d for d in MATCHED_DIR.iterdir() if d.is_dir()])

        if not pairs:
            return None

        # Take first pair
        next_pair = pairs[0]

        # Initialize started_at if first pair
        if self.state["started_at"] is None:
            self.state["started_at"] = datetime.now().isoformat()

        # Update state
        self.state["current_pair"] = str(next_pair)
        self._save_state()

        # Find review, source, and metadata files
        review_path = next_pair / "review.txt"
        metadata_path = next_pair / "metadata.json"

        # Find source file (could be .txt, .pdf, .docx, etc.)
        source_files = [f for f in next_pair.iterdir() if f.name.startswith("source.")]

        if not review_path.exists():
            self._log(next_pair.name, "ERROR", "review.txt not found")
            self.fail(next_pair.name, "review.txt not found")
            return self.get_next()

        if not source_files:
            self._log(next_pair.name, "ERROR", "source file not found")
            self.fail(next_pair.name, "source file not found")
            return self.get_next()

        source_path = source_files[0]

        # Read review content
        try:
            review_content = review_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            self._log(next_pair.name, "ERROR", f"Cannot read review.txt: {e}")
            self.fail(next_pair.name, f"Cannot read review.txt: {e}")
            return self.get_next()

        # Read metadata
        metadata = {}
        if metadata_path.exists():
            try:
                with metadata_path.open("r") as f:
                    metadata = json.load(f)
            except Exception as e:
                print(f"WARNING: Cannot read metadata.json: {e}", file=sys.stderr)

        self._log(next_pair.name, "PROCESSING", "Pair loaded for processing")

        return {
            "pair_dir": str(next_pair),
            "pair_name": next_pair.name,
            "review_path": str(review_path),
            "review_content": review_content,
            "source_path": str(source_path),
            "source_type": source_path.suffix,
            "metadata": metadata,
        }

    def confirm(self, pair_name: str) -> bool:
        """
        Confirm processing complete, delete source pair directory.

        Args:
            pair_name: Name of pair directory to confirm

        Returns:
            True if successful, False otherwise
        """
        # Verify this is the current pair
        if self.state["current_pair"] is None:
            print("ERROR: No pair currently being processed", file=sys.stderr)
            return False

        current_path = Path(self.state["current_pair"])
        if current_path.name != pair_name:
            print(
                f"ERROR: Current pair is {current_path.name}, not {pair_name}",
                file=sys.stderr,
            )
            return False

        # Delete source pair directory
        try:
            shutil.rmtree(current_path)
            self._log(pair_name, "COMPLETED", "Processing confirmed, source deleted")
        except Exception as e:
            print(f"ERROR: Cannot delete pair directory: {e}", file=sys.stderr)
            self._log(pair_name, "ERROR", f"Cannot delete: {e}")
            return False

        # Update state
        self.state["current_pair"] = None
        self.state["processed_count"] += 1
        self._save_state()

        return True

    def fail(self, pair_name: str, reason: str) -> bool:
        """
        Mark pair as failed, move to failed directory.

        Args:
            pair_name: Name of pair that failed
            reason: Reason for failure

        Returns:
            True if successful, False otherwise
        """
        # Find the pair directory
        if self.state["current_pair"]:
            source_path = Path(self.state["current_pair"])
        else:
            source_path = MATCHED_DIR / pair_name

        if not source_path.exists():
            print(f"ERROR: Pair directory not found: {source_path}", file=sys.stderr)
            return False

        # Move to failed directory
        try:
            dest_path = FAILED_DIR / source_path.name
            shutil.move(str(source_path), str(dest_path))
            self._log(pair_name, "FAILED", reason)
        except Exception as e:
            print(f"ERROR: Cannot move pair to failed: {e}", file=sys.stderr)
            self._log(pair_name, "ERROR", f"Cannot move to failed: {e}")
            return False

        # Update state
        self.state["current_pair"] = None
        self.state["failed_count"] += 1
        self._save_state()

        return True

    def status(self) -> dict:
        """
        Get processing status.

        Returns:
            dict with processing statistics
        """
        # Count remaining pairs
        remaining = len([d for d in MATCHED_DIR.iterdir() if d.is_dir()])

        return {
            "remaining": remaining,
            "processed": self.state["processed_count"],
            "failed": self.state["failed_count"],
            "current_pair": self.state.get("current_pair"),
            "started_at": self.state.get("started_at"),
            "last_updated": self.state.get("last_updated"),
        }

    def reset(self) -> None:
        """
        Reset processing state.

        WARNING: This does not restore deleted pairs!
        Use only for testing or to restart processing.
        """
        self.state = {
            "current_pair": None,
            "processed_count": 0,
            "failed_count": 0,
            "started_at": None,
            "last_updated": None,
        }
        self._save_state()
        print("State reset. Deleted pairs cannot be recovered!", file=sys.stderr)


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    processor = ReviewBatchProcessor()
    command = sys.argv[1]

    if command == "next":
        result = processor.get_next()
        if result is None:
            print("No pairs remaining to process")
            sys.exit(0)
        # Output as JSON for easy parsing (exclude review_content for brevity)
        output = {k: v for k, v in result.items() if k != "review_content"}
        print(json.dumps(output, indent=2))

    elif command == "confirm":
        if len(sys.argv) < 3:
            print("ERROR: Missing pair_name argument", file=sys.stderr)
            sys.exit(1)
        pair_name = sys.argv[2]
        if processor.confirm(pair_name):
            print(f"Confirmed: {pair_name}")
        else:
            sys.exit(1)

    elif command == "fail":
        if len(sys.argv) < 4:
            print("ERROR: Missing pair_name or reason argument", file=sys.stderr)
            sys.exit(1)
        pair_name = sys.argv[2]
        reason = " ".join(sys.argv[3:])
        if processor.fail(pair_name, reason):
            print(f"Failed: {pair_name}")
        else:
            sys.exit(1)

    elif command == "status":
        status = processor.status()
        print(json.dumps(status, indent=2))

    elif command == "reset":
        confirm = input(
            "Are you sure you want to reset state? This cannot restore deleted pairs! (yes/no): "
        )
        if confirm.lower() == "yes":
            processor.reset()
            print("State reset")
        else:
            print("Cancelled")

    else:
        print(f"ERROR: Unknown command: {command}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
