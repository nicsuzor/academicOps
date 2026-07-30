import os
import glob

def fix_file(path):
    with open(path, "r") as f:
        content = f.read()

    if "import degraded" in content:
        content = content.replace("import degraded\n", "import sys\n")
        content = content.replace("degraded.report(", "print('DEGRADED: ', ")
        content = content.replace("DEGRADED_CONFIG,", "")
        
    with open(path, "w") as f:
        f.write(content)

for p in glob.glob("plugins/rbg/hooks/*.py"):
    fix_file(p)
