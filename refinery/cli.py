#!/usr/bin/env python3
import click
from engineer import Engineer

@click.group()
def main():
    """Refinery: Automated Merge Queue."""
    pass

@main.command()
def scan():
    """Scan for tasks in REVIEW status and merge them."""
    eng = Engineer()
    eng.scan_and_merge()

if __name__ == "__main__":
    main()
