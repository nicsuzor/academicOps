#!/usr/bin/env python3
"""
PDF Generation Script

Converts markdown files to professionally formatted PDFs using pandoc and weasyprint.
Applies custom academic styling with Roboto fonts.

Usage:
    python generate_pdf.py <input.md> [output.pdf] [--title "Document Title"]

Requirements:
    - pandoc
    - weasyprint (installed via: uv tool install weasyprint)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Default signature path (user data, not in skill)
DEFAULT_SIGNATURE_PATH = Path(os.environ.get("ACA_DATA", "")) / "assets" / "signature.png"


def detect_document_type(input_file: Path) -> str:
    """
    Detect whether the document is a letter or academic document.

    A document is considered a letter if:
    - It has no h1 heading, OR
    - The first few lines contain typical letter elements (date, recipient, salutation)

    Args:
        input_file: Path to markdown file

    Returns:
        "letter" or "academic"
    """
    try:
        content = input_file.read_text(encoding="utf-8")
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        # Check first 10 lines for h1 heading
        has_h1 = False
        for line in lines[:10]:
            if line.startswith("# "):
                has_h1 = True
                break

        # If no h1, likely a letter
        if not has_h1:
            return "letter"

        # Check for letter patterns in first few lines
        first_content = "\n".join(lines[:10]).lower()
        letter_patterns = ["dear ", "re:", "sincerely", "regards", "best,"]

        if any(pattern in first_content for pattern in letter_patterns):
            return "letter"

        return "academic"

    except Exception:
        # Default to academic if we can't read the file
        return "academic"


def generate_pdf(
    input_file: Path,
    output_file: Path | None = None,
    title: str | None = None,
    css_file: Path | None = None,
    doc_type: str | None = None,
) -> int:
    """
    Generate a PDF from a markdown file.

    Args:
        input_file: Path to input markdown file
        output_file: Path to output PDF file (defaults to input filename with .pdf extension)
        title: Document title for metadata (defaults to filename)
        css_file: Path to custom CSS file (defaults to auto-detected style)
        doc_type: Document type ("letter" or "academic", auto-detected if None)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Determine output path
    if output_file is None:
        output_file = input_file.with_suffix(".pdf")

    # Determine title
    if title is None:
        title = input_file.stem.replace("-", " ").replace("_", " ").title()

    # Auto-detect document type if not specified
    if doc_type is None:
        doc_type = detect_document_type(input_file)

    # Determine CSS path based on document type
    if css_file is None:
        script_dir = Path(__file__).parent
        skill_dir = script_dir.parent
        if doc_type == "letter":
            css_file = skill_dir / "assets" / "letter-style.css"
        else:
            css_file = skill_dir / "assets" / "academic-style.css"

    # Verify CSS exists
    if not css_file.exists():
        print(f"Error: CSS file not found: {css_file}", file=sys.stderr)
        return 1

    # Verify input exists
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        return 1

    # Build pandoc command
    cmd = [
        "pandoc",
        str(input_file),
        "-o",
        str(output_file),
        "--pdf-engine=weasyprint",
        f"--metadata=title:{title}",
        f"--css={css_file}",
    ]

    # Execute pandoc
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Print any warnings (weasyprint often has minor CSS warnings)
        if result.stderr:
            print("Warnings:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)

        print(f"✓ PDF generated successfully: {output_file}")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"Error generating PDF: {e}", file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        return 1
    except FileNotFoundError:
        print("Error: pandoc not found. Please install pandoc.", file=sys.stderr)
        return 1


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Convert markdown to professionally formatted PDF"
    )
    parser.add_argument("input", type=Path, help="Input markdown file")
    parser.add_argument("output", type=Path, nargs="?", help="Output PDF file (optional)")
    parser.add_argument("--title", "-t", help="Document title for metadata")
    parser.add_argument("--css", type=Path, help="Custom CSS file (optional)")
    parser.add_argument(
        "--type",
        choices=["letter", "academic"],
        help='Document type: "letter" or "academic" (auto-detected if not specified)',
    )
    args = parser.parse_args()

    sys.exit(generate_pdf(args.input, args.output, args.title, args.css, args.type))


if __name__ == "__main__":
    main()
