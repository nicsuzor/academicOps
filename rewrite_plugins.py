import os
import glob


def rewrite_plugin(path):
    with open(path, "r") as f:
        content = f.read()

    # Rewrite imports
    content = content.replace("from context import HookContext", "from dispatch import HookContext")
    content = content.replace(
        "from result import Result, warn", "from dispatch import Result, warn"
    )
    content = content.replace(
        "from result import Result, refuse", "from dispatch import Result, refuse"
    )
    content = content.replace("import result\n", "import dispatch as result\n")

    # Degraded module replacement - just print to stderr
    if "import degraded" in content:
        content = content.replace("import degraded\n", "import sys\n")
        # simplistic replacement for degraded.report
        content = content.replace("degraded.report(", 'print("DEGRADED: ", ')
        content = content.replace("evaluator.DEGRADED_EVALUATOR,", "")

    # Messages replacement
    if "import messages" in content:
        content = content.replace("import messages\n", "from dispatch import load_message_pair\n")
        content = content.replace(
            "messages.load_pair(ctx.hooks_dir, ", "load_message_pair(ctx.hooks_dir, "
        )
        content = content.replace(
            "messages.load_pair(ctx.hooks_dir,", "load_message_pair(ctx.hooks_dir,"
        )
        content = content.replace(
            'ctx.message("ruleset")', 'load_message_pair(ctx.hooks_dir, "ruleset")[0]'
        )

    with open(path, "w") as f:
        f.write(content)


for p in glob.glob("plugins/*/hooks/handlers.py"):
    rewrite_plugin(p)
