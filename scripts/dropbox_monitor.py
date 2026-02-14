#!/usr/bin/env python3
import argparse
import logging
import sys
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Add project root to path
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

# Import processor
try:
    from scripts.lib.incoming_processor import process_incoming_file
except ImportError:
    # Fallback if running from root
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from lib.incoming_processor import process_incoming_file

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


class IncomingHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        logger.info(f"New file detected: {event.src_path}")
        self.process_file(Path(str(event.src_path)))

    def process_file(self, file_path):
        process_incoming_file(file_path)


def main():
    parser = argparse.ArgumentParser(description="Monitor ~/incoming for new files.")
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path.home() / "incoming",
        help="Directory to monitor",
    )
    args = parser.parse_args()

    watch_dir = args.dir
    if not watch_dir.exists():
        logger.warning(f"Directory {watch_dir} does not exist. Creating it...")
        watch_dir.mkdir(parents=True, exist_ok=True)

    event_handler = IncomingHandler()
    observer = Observer()
    observer.schedule(event_handler, str(watch_dir), recursive=False)
    observer.start()
    logger.info(f"Monitoring {watch_dir} for new files... (Press Ctrl+C to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
