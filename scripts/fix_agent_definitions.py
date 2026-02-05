import re
import yaml
from pathlib import Path

def fix_agent_definition(file_path):
    print(f"Processing {file_path}...")
    with open(file_path, 'r') as f:
        content = f.read()

    # Split frontmatter
    match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
    if not match:
        print(f"  Skipping {file_path}: No frontmatter found")
        return

    frontmatter_raw = match.group(1)
    body = match.group(2)

    try:
        # Sanitize hanging list items before loading
        lines = frontmatter_raw.split('\n')
        reconstructed_yaml = ""
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if re.match(r'^\w+:', line):
                reconstructed_yaml += line + "\n"
            elif stripped.startswith('- '):
                # We drop ALL list items unless we are sure.
                # Since we are dropping 'tools' anyway, we don't need to preserve list items for tools.
                # And we are dropping 'tags' etc.
                # So effectively we drop ALL lists from frontmatter for these agents
                # as they don't seem to have other lists (like 'params'?)
                # Let's check if there are other keys that use lists.
                # 'model' is scalar. 'name', 'description' are scalar.
                # So safe to drop all list items for now to be clean.
                pass
            else:
                reconstructed_yaml += line + "\n"

        data = yaml.safe_load(reconstructed_yaml)
    except yaml.YAMLError as e:
        print(f"  YAML Parse Error: {e}")
        return

    # Remove invalid keys
    for key in ['category', 'permalink', 'type', 'tags', 'tools']: # Removed tools!
        if key in data:
            del data[key]

    # Dump
    new_frontmatter = yaml.dump(data, default_flow_style=False, sort_keys=False).strip()
    
    with open(file_path, 'w') as f:
        f.write(f"---\n{new_frontmatter}\n---\n{body}")
    print(f"  Fixed {file_path} (Removed tools)")

def main():
    agents_dir = Path("aops-core/agents")
    for file_path in agents_dir.glob("*.md"):
        fix_agent_definition(file_path)

if __name__ == "__main__":
    main()
