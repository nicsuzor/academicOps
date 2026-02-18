#!/usr/bin/env python3
"""Show Path CLI - Terminal version of the Overwhelm Dashboard's 'Your Path'.

Displays a narrative timeline of recent work across sessions, prioritizing
human intent (task titles) over mechanical metadata (IDs).
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Add aops-core to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from lib.path_reconstructor import reconstruct_path, EventType

console = Console()

def format_time(dt):
    if not dt:
        return ""
    return dt.strftime("%H:%M")

@click.command()
@click.option("--hours", "-h", default=24, help="Look back N hours (default: 24)")
def main(hours: int):
    """Show your recent path across sessions."""
    # Force ACA_DATA if not set
    if "ACA_DATA" not in os.environ:
        os.environ["ACA_DATA"] = str(Path.home() / "brain")

    path = reconstruct_path(hours=hours)

    if not path.threads:
        console.print("[dim]No recent activity found.[/dim]")
        return

    # 1. Unfinished Tasks (Triage)
    if path.abandoned_work:
        console.print()
        console.print(f"[bold yellow]📋 UNFINISHED TASKS ({len(path.abandoned_work)})[/bold yellow]")
        
        # Group by project
        by_project = {}
        for item in path.abandoned_work:
            proj = item.project or "unknown"
            if proj not in by_project:
                by_project[proj] = []
            by_project[proj].append(item)
            
        for proj, items in sorted(by_project.items()):
            console.print(f"[dim cyan]{proj.upper()}[/dim cyan]")
            for item in items:
                title = item.resolved_title or item.description or item.task_id
                console.print(f"  [yellow]□[/yellow] {title} [dim]({item.task_id})[/dim]")
        console.print()

    # 2. Path Timeline
    console.print(f"[bold]YOUR PATH (Last {hours}h)[/bold]")
    
    # Group threads by project
    threads_by_project = {}
    for thread in path.threads:
        proj = thread.project or "unknown"
        if proj not in threads_by_project:
            threads_by_project[proj] = []
        threads_by_project[proj].append(thread)

    for proj, threads in threads_by_project.items():
        console.print(Panel(f"[bold cyan]{proj.upper()}[/bold cyan]", expand=False, border_style="dim"))
        
        for thread in threads:
            # Session Header
            sid = thread.session_id[:8]
            goal = thread.hydrated_intent or thread.initial_goal
            # Clean up goal for display
            if goal:
                goal = goal.replace("\n", " ").strip()[:100]
            
            header = Text()
            header.append(f"● {format_time(thread.start_time)} ", style="green")
            header.append(f"{goal or 'Session started'} ", style="white bold")
            header.append(f"({sid})", style="dim")
            
            if thread.git_branch:
                 header.append(f"\n  └─ branch: {thread.git_branch}", style="dim italic")

            console.print(header)
            
            # Events
            for event in thread.events:
                # Skip low signal events
                if event.event_type in (EventType.SESSION_START,):
                    continue
                    
                narrative = event.render_narrative()
                time_str = format_time(event.timestamp)
                
                # Style based on type
                style = "white"
                prefix = "  "
                if event.event_type == EventType.TASK_COMPLETE:
                    style = "green"
                    prefix = "  ✓ "
                elif event.event_type == EventType.TASK_CREATE:
                    style = "blue"
                    prefix = "  + "
                elif event.event_type == EventType.TASK_ABANDON:
                    style = "yellow"
                    prefix = "  □ "
                elif event.event_type == EventType.USER_PROMPT:
                    style = "dim"
                    prefix = "  > "
                
                console.print(f"{prefix}[dim]{time_str}[/dim] [{style}]{narrative}[/{style}]")
            
            console.print() # Spacer between threads

if __name__ == "__main__":
    main()
