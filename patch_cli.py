import re

with open("polecat/cli.py", "r") as f:
    content = f.read()

# 1. replace nuke argument
content = re.sub(
    r'@main\.command\(\)\n@click\.argument\("task_id"\)\n@click\.option\("--force", "-f", is_flag=True, help="Delete even if work is not merged"\)\n@click\.pass_context\ndef nuke\(ctx, task_id, force\):',
    '@main.command()\n@click.argument("target", required=False)\n@click.option("--force", "-f", is_flag=True, help="Delete even if work is not merged")\n@click.pass_context\ndef nuke(ctx, target, force):',
    content
)

with open("polecat/cli.py", "w") as f:
    f.write(content)
