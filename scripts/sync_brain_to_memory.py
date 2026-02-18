#!/usr/bin/env python3
"""Sync ~/brain markdown files to the remote memory MCP server.

Walks ~/brain recursively, chunks markdown by headers, and stores each
chunk via the memory MCP's store_memory tool. Uses a local manifest file
to skip files that haven't changed since the last sync.

Usage:
    uv run python scripts/sync_brain_to_memory.py [OPTIONS]

Options:
    --brain-dir PATH       Path to brain directory (default: ~/brain)
    --dry-run              Show what would be synced without storing
    --max-files INT        Limit number of files to process (for testing)
    --skip-dirs TEXT        Comma-separated dirs to skip (default: .git,.agent)
    --concurrency INT      Max concurrent requests (default: 5)
    --force                Ignore manifest, re-sync everything
    --verbose              Show per-file progress
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

from fastmcp import Client
from fastmcp.client.auth import BearerAuth

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MEMORY_URL = os.environ.get(
    "MEMORY_SERVER_URL",
    "http://services.stoat-musical.ts.net:8026/mcp",
)
API_KEY = os.environ.get("MCP_MEMORY_API_KEY")

DEFAULT_BRAIN_DIR = Path.home() / "brain"
DEFAULT_SKIP_DIRS = {".git", ".agent"}
MANIFEST_PATH = Path.home() / ".cache" / "brain-sync-manifest.json"

MAX_CHUNK_SIZE = 3000  # chars – keep embeddings focused
SMALL_FILE_THRESHOLD = 1500  # chars – store whole if below this

# ---------------------------------------------------------------------------
# Manifest (dedup)
# ---------------------------------------------------------------------------


def load_manifest(path: Path) -> dict:
    """Load the sync manifest from disk.

    Returns dict mapping relative file paths to
    {"mtime": float, "content_hash": str, "chunks": int}.
    """
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def discover_files(
    brain_dir: Path,
    skip_dirs: set[str],
    max_files: int | None = None,
) -> list[Path]:
    """Walk brain_dir for .md files, respecting skip_dirs."""
    files: list[Path] = []
    for root, dirs, filenames in os.walk(brain_dir):
        # Prune skipped directories in-place
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in sorted(filenames):
            if fname.endswith(".md"):
                files.append(Path(root) / fname)
                if max_files and len(files) >= max_files:
                    return files
    return files


# ---------------------------------------------------------------------------
# Markdown chunking
# ---------------------------------------------------------------------------


def chunk_markdown(text: str, source_path: str) -> list[dict]:
    """Split markdown text into chunks by headers.

    Small files (<SMALL_FILE_THRESHOLD) are returned as a single chunk.
    Large sections (>MAX_CHUNK_SIZE) are split further at paragraph boundaries.

    Returns list of {"content": str, "section": str} dicts.
    """
    if len(text) <= SMALL_FILE_THRESHOLD:
        return [{"content": text.strip(), "section": ""}]

    # Split on h1/h2/h3 headers
    parts = re.split(r"(?=^#{1,3}\s)", text, flags=re.MULTILINE)
    chunks: list[dict] = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Extract section title from first line if it's a header
        first_line = part.split("\n", 1)[0]
        section = first_line.lstrip("#").strip() if first_line.startswith("#") else ""

        if len(part) <= MAX_CHUNK_SIZE:
            chunks.append({"content": part, "section": section})
        else:
            # Split oversized sections at paragraph boundaries
            chunks.extend(_split_large_section(part, section))

    return chunks


def _split_large_section(text: str, section: str) -> list[dict]:
    """Split an oversized section into smaller chunks at paragraph boundaries."""
    paragraphs = re.split(r"\n\n+", text)
    chunks: list[dict] = []
    current = ""

    for para in paragraphs:
        if current and len(current) + len(para) + 2 > MAX_CHUNK_SIZE:
            chunks.append({"content": current.strip(), "section": section})
            current = para
        else:
            current = current + "\n\n" + para if current else para

    if current.strip():
        chunks.append({"content": current.strip(), "section": section})

    return chunks


# ---------------------------------------------------------------------------
# MCP storage
# ---------------------------------------------------------------------------


def build_tags(rel_path: Path) -> list[str]:
    """Build tags for a memory chunk."""
    parts = rel_path.parts
    top_dir = parts[0] if len(parts) > 1 else "root"
    filename = rel_path.name
    return ["brain", top_dir, f"source_file:{filename}"]


def build_metadata(rel_path: Path) -> dict:
    return {
        "source": str(rel_path),
        "file_type": "md",
        "source_dir": "brain",
    }


async def store_chunk(
    client: Client,
    chunk: dict,
    rel_path: Path,
    dry_run: bool = False,
    verbose: bool = False,
    max_retries: int = 3,
) -> bool:
    """Store a single chunk via the MCP store_memory tool.

    Returns True if stored successfully (or dry_run), False on error.
    Raises ConnectionError if the client connection is dead (for worker to handle).
    """
    tags = build_tags(rel_path)
    metadata = build_metadata(rel_path)

    if chunk["section"]:
        metadata["section"] = chunk["section"]

    if dry_run:
        if verbose:
            preview = chunk["content"][:80].replace("\n", " ")
            print(f"  [dry-run] Would store chunk ({len(chunk['content'])} chars): {preview}...")
        return True

    for attempt in range(max_retries):
        try:
            await client.call_tool(
                "store_memory",
                {
                    "content": chunk["content"],
                    "tags": tags,
                    "metadata": metadata,
                    "memory_type": "note",
                },
            )
            return True
        except Exception as e:
            err_str = str(e).lower()
            if "not connected" in err_str:
                raise ConnectionError(f"Client disconnected: {e}") from e
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                if verbose:
                    print(f"  RETRY ({attempt + 1}/{max_retries}) {rel_path}: {e}", file=sys.stderr)
                await asyncio.sleep(wait)
            else:
                print(f"  ERROR storing chunk for {rel_path}: {e}", file=sys.stderr)
                return False
    return False


# ---------------------------------------------------------------------------
# File processing
# ---------------------------------------------------------------------------


async def process_file(
    client: Client,
    file_path: Path,
    brain_dir: Path,
    manifest: dict,
    semaphore: asyncio.Semaphore,
    dry_run: bool = False,
    force: bool = False,
    verbose: bool = False,
) -> dict:
    """Process a single markdown file.

    Returns {"path": str, "status": str, "chunks": int}.
    """
    rel_path = file_path.relative_to(brain_dir)
    rel_str = str(rel_path)

    try:
        mtime = file_path.stat().st_mtime
    except FileNotFoundError:
        if verbose:
            print(f"  SKIP (not found): {rel_str}")
        return {"path": rel_str, "status": "not_found", "chunks": 0}

    # Check manifest for dedup
    if not force and rel_str in manifest:
        entry = manifest[rel_str]
        if entry.get("mtime") == mtime:
            if verbose:
                print(f"  SKIP (unchanged): {rel_str}")
            return {"path": rel_str, "status": "skipped", "chunks": 0}

    text = file_path.read_text(encoding="utf-8", errors="replace")

    if not text.strip():
        if verbose:
            print(f"  SKIP (empty): {rel_str}")
        return {"path": rel_str, "status": "empty", "chunks": 0}

    chunks = chunk_markdown(text, rel_str)

    if verbose:
        print(f"  PROCESS: {rel_str} ({len(chunks)} chunk(s), {len(text)} chars)")

    stored = 0
    async with semaphore:
        for chunk in chunks:
            if not chunk["content"].strip():
                continue
            ok = await store_chunk(client, chunk, rel_path, dry_run, verbose)
            if ok:
                stored += 1

    # Update manifest
    if not dry_run and stored > 0:
        manifest[rel_str] = {
            "mtime": mtime,
            "content_hash": content_hash(text),
            "chunks": stored,
            "synced_at": time.time(),
        }

    return {"path": rel_str, "status": "stored" if stored > 0 else "failed", "chunks": stored}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def run(args: argparse.Namespace) -> None:
    if not API_KEY:
        print("ERROR: MCP_MEMORY_API_KEY environment variable must be set.", file=sys.stderr)
        sys.exit(1)

    brain_dir = Path(args.brain_dir).expanduser().resolve()
    if not brain_dir.is_dir():
        print(f"ERROR: Brain directory not found: {brain_dir}", file=sys.stderr)
        sys.exit(1)

    skip_dirs = set(args.skip_dirs.split(","))

    print(f"Brain directory: {brain_dir}")
    print(f"Skip dirs: {skip_dirs}")
    print(f"Concurrency: {args.concurrency}")
    if args.dry_run:
        print("DRY RUN: no memories will be stored")
    if args.force:
        print("FORCE: ignoring manifest, re-syncing everything")
    print()

    # Discover files
    files = discover_files(brain_dir, skip_dirs, args.max_files)
    print(f"Found {len(files)} markdown files")

    # Load manifest
    manifest = {} if args.force else load_manifest(MANIFEST_PATH)
    print(f"Manifest entries: {len(manifest)}")
    print()

    # Worker pool: each worker gets its own client connection
    file_queue: asyncio.Queue[Path] = asyncio.Queue()
    for f in files:
        await file_queue.put(f)

    results: list[dict] = []
    results_lock = asyncio.Lock()
    manifest_lock = asyncio.Lock()
    progress = {"done": 0, "total": len(files)}

    MANIFEST_SAVE_INTERVAL = 50  # flush manifest every N files

    def _status_char(status: str) -> str:
        return {"stored": ".", "skipped": "s", "empty": "e",
                "not_found": "!", "failed": "x"}.get(status, "?")

    async def _record_result(result: dict) -> None:
        """Record a result and periodically flush the manifest."""
        async with results_lock:
            results.append(result)
            progress["done"] += 1
            done = progress["done"]

        if not args.verbose:
            print(_status_char(result["status"]), end="", flush=True)
            if done % 50 == 0:
                print(f" [{done}/{progress['total']}]")

        # Periodically save manifest so progress survives crashes
        if not args.dry_run and done % MANIFEST_SAVE_INTERVAL == 0:
            async with manifest_lock:
                save_manifest(MANIFEST_PATH, manifest)

    async def worker(worker_id: int) -> None:
        """Process files from the queue with a dedicated client connection."""
        semaphore = asyncio.Semaphore(1)

        while not file_queue.empty():
            try:
                file_path = file_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            client = Client(MEMORY_URL, auth=BearerAuth(token=API_KEY))
            try:
                async with client:
                    # Process first file
                    result = await process_file(
                        client, file_path, brain_dir, manifest, semaphore,
                        args.dry_run, args.force, args.verbose,
                    )
                    await _record_result(result)

                    # Keep processing while connected
                    while not file_queue.empty():
                        try:
                            file_path = file_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                        result = await process_file(
                            client, file_path, brain_dir, manifest, semaphore,
                            args.dry_run, args.force, args.verbose,
                        )
                        await _record_result(result)

            except (ConnectionError, OSError) as e:
                print(f"\n  Worker {worker_id} reconnecting: {e}", file=sys.stderr)
                await _record_result({
                    "path": str(file_path.relative_to(brain_dir)),
                    "status": "failed", "chunks": 0,
                })
                continue
            except Exception as e:
                print(f"\n  Worker {worker_id} error: {e}", file=sys.stderr)
                await _record_result({
                    "path": str(file_path.relative_to(brain_dir)),
                    "status": "failed", "chunks": 0,
                })
                continue

    workers = [asyncio.create_task(worker(i)) for i in range(args.concurrency)]
    await asyncio.gather(*workers)

    if not args.verbose:
        print()  # newline after progress dots

    # Final manifest save
    if not args.dry_run:
        save_manifest(MANIFEST_PATH, manifest)
        print(f"\nManifest saved to {MANIFEST_PATH} ({len(manifest)} entries)")

    # Summary
    stored = sum(1 for r in results if r["status"] == "stored")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    empty = sum(1 for r in results if r["status"] == "empty")
    not_found = sum(1 for r in results if r["status"] == "not_found")
    failed = sum(1 for r in results if r["status"] == "failed")
    total_chunks = sum(r["chunks"] for r in results)

    print(f"\n--- Summary ---")
    print(f"Files processed: {len(results)}")
    print(f"  Stored:    {stored} ({total_chunks} chunks)")
    print(f"  Skipped:   {skipped} (unchanged)")
    print(f"  Empty:     {empty}")
    print(f"  Not found: {not_found}")
    print(f"  Failed:    {failed}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync ~/brain markdown files to memory MCP server",
    )
    parser.add_argument(
        "--brain-dir",
        default=str(DEFAULT_BRAIN_DIR),
        help=f"Path to brain directory (default: {DEFAULT_BRAIN_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without storing",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Limit number of files to process (for testing)",
    )
    parser.add_argument(
        "--skip-dirs",
        default=",".join(DEFAULT_SKIP_DIRS),
        help="Comma-separated dirs to skip (default: .git,.agent)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max concurrent requests (default: 5)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore manifest, re-sync everything",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show per-file progress",
    )
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
