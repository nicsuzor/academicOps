import re

with open("polecat/cli.py", "r") as f:
    content = f.read()

# Delete nuke-crew
nuke_crew_code = '''@main.command("nuke-crew")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Delete even if work is not merged")
@click.pass_context
def nuke_crew(ctx, name, force):
    """Remove a crew worker and their worktrees."""
    manager = PolecatManager(home_dir=ctx.obj.get("home"))
    try:
        manager.nuke_crew(name, force=force)
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)'''

if nuke_crew_code in content:
    content = content.replace(nuke_crew_code + "\n\n\n", "")
else:
    print("Could not find nuke-crew code exactly. Using regex.")
    content = re.sub(
        r'@main\.command\("nuke-crew"\).*?sys\.exit\(1\)\n\n\n',
        '',
        content,
        flags=re.DOTALL
    )

with open("polecat/cli.py", "w") as f:
    f.write(content)
