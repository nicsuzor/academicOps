import logging
import mimetypes
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def get_mime_type(file_path: Path) -> str:
    # Try mimetypes first
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        return mime_type

    # Fallback to 'file' command
    try:
        result = subprocess.run(
            ["file", "--mime-type", "-b", str(file_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "application/octet-stream"


def process_incoming_file(file_path: Path):
    """
    Process a file from ~/incoming.
    Determines type, converts if necessary, and moves to destination.
    """
    if not file_path.exists():
        logger.warning(f"File {file_path} vanished before processing.")
        return

    logger.info(f"Processing: {file_path.name}")

    # Wait for file write to complete (simple heuristic: file size constant for 1s?)
    # For now, assume watchdog event implies it's ready, but with large files careful.
    # We might need a retry loop or check open handles.

    mime_type = get_mime_type(file_path)
    logger.info(f"Detected MIME: {mime_type}")

    # Routing Logic
    dest_root = Path.home() / "processed"  # Default destination root

    if mime_type == "application/pdf":
        dest_dir = dest_root / "docs"
        try:
            from pdfminer.high_level import extract_text

            text = extract_text(file_path)
            md_path = dest_dir / (file_path.stem + ".md")
            dest_dir.mkdir(parents=True, exist_ok=True)

            with open(md_path, "w") as f:
                f.write(f"# {file_path.stem}\n\n")
                f.write(text)

            notify_user(f"Converted PDF: {file_path.name}", f"Saved to {md_path}")

            # Also move the original? Or just keep it?
            # Requirement says "File to appropriate location".
            # Probably move original to archive or keep alongside.
            # I'll move original to docs/pdf_archive or just docs/
            pass
        except ImportError:
            logger.warning("pdfminer.six not found, skipping conversion.")
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")

    elif mime_type.startswith("image/"):
        dest_dir = dest_root / "images"
    elif mime_type.startswith("text/") or file_path.suffix in [
        ".md",
        ".txt",
        ".py",
        ".js",
        ".json",
    ]:
        dest_dir = dest_root / "notes"
    else:
        dest_dir = dest_root / "misc"

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file_path.name

    # Handle duplicates
    if dest_path.exists():
        timestamp = int(subprocess.check_output(["date", "+%s"]).strip())
        dest_path = dest_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"

    logger.info(f"Moving to {dest_path}")
    try:
        shutil.move(str(file_path), str(dest_path))
        # Notify user (TODO)
        notify_user(f"Processed {file_path.name}", f"Moved to {dest_path}")
    except Exception as e:
        logger.error(f"Failed to move {file_path}: {e}")


def notify_user(title, message):
    """
    Send notification to user.
    Tries 'notify-send' first, then logs.
    """
    logger.info(f"NOTIFICATION: {title} - {message}")

    notify_cmd = shutil.which("notify-send")
    if notify_cmd:
        try:
            subprocess.run(
                [notify_cmd, title, message],
                check=False,  # Don't crash if notification fails
            )
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
