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
import subprocess
import sys
from pathlib import Path


def generate_pdf(
    input_file: Path,
    output_file: Path | None = None,
    title: str | None = None,
    css_file: Path | None = None,
) -> int:
    """
    Generate a PDF from a markdown file.

    Args:
        input_file: Path to input markdown file
        output_file: Path to output PDF file (defaults to input filename with .pdf extension)
        title: Document title for metadata (defaults to filename)
        css_file: Path to custom CSS file (defaults to bundled academic-style.css)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Determine output path
    if output_file is None:
        output_file = input_file.with_suffix(".pdf")

    # Determine title
    if title is None:
        title = input_file.stem.replace("-", " ").replace("_", " ").title()

    # Determine CSS path
    if css_file is None:
        script_dir = Path(__file__).parent
        skill_dir = script_dir.parent
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
    parser.add_argument(
        "output", type=Path, nargs="?", help="Output PDF file (optional)"
    )
    parser.add_argument("--title", "-t", help="Document title for metadata")
    parser.add_argument("--css", type=Path, help="Custom CSS file (optional)")

    args = parser.parse_args()

    sys.exit(generate_pdf(args.input, args.output, args.title, args.css))


if __name__ == "__main__":
    main()
