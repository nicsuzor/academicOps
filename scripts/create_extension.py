import json
import os
import sys
from pathlib import Path

def main():
    # Paths
    aops_path = os.environ.get("AOPS")
    aca_data_path = os.environ.get("ACA_DATA")
    
    if not aops_path or not aca_data_path:
        print("Error: AOPS and ACA_DATA environment variables must be set.")
        sys.exit(1)

    plugin_root = os.path.join(aops_path, "aops-core")

    # Create dist directory
    dist_dir = os.path.join(aops_path, "dist")
    os.makedirs(dist_dir, exist_ok=True)

    # Symlink required resources
    for item in ["skills", "GEMINI.md"]:
        src = os.path.join(plugin_root, item)
        dst = os.path.join(dist_dir, item)
        if os.path.exists(src):
            if os.path.islink(dst) or os.path.exists(dst):
                if os.path.isdir(dst) and not os.path.islink(dst):
                     import shutil
                     shutil.rmtree(dst)
                else:
                     os.remove(dst)
            os.symlink(src, dst)

    # Package hooks (selective symlink to exclude hooks.json)
    hooks_src_dir = os.path.join(plugin_root, "hooks")
    hooks_dst_dir = os.path.join(dist_dir, "hooks")
    
    if os.path.exists(hooks_dst_dir):
        if os.path.islink(hooks_dst_dir):
            os.remove(hooks_dst_dir)
        else:
            import shutil
            shutil.rmtree(hooks_dst_dir)
    
    os.makedirs(hooks_dst_dir, exist_ok=True)
    
    if os.path.exists(hooks_src_dir):
        for item in os.listdir(hooks_src_dir):
            if item == "hooks.json":
                continue
            
            s = os.path.join(hooks_src_dir, item)
            d = os.path.join(hooks_dst_dir, item)
            if os.path.exists(d): # Clean up if exists
                 if os.path.islink(d) or os.path.isfile(d):
                      os.remove(d)
                 else:
                      shutil.rmtree(d)
            os.symlink(s, d)

    # Read Claude hooks configuration
    hooks_json_path = os.path.join(hooks_src_dir, "hooks.json")
    claude_hooks = {}
    if os.path.exists(hooks_json_path):
        with open(hooks_json_path, "r") as f:
            claude_hooks = json.load(f).get("hooks", {})

    # Mapping: Claude Event -> Gemini Event(s)
    CLAUDE_TO_GEMINI = {
        "SessionStart": ["SessionStart"],
        "PreToolUse": ["BeforeTool"],
        "PostToolUse": ["AfterTool"],
        "UserPromptSubmit": ["BeforeAgent"],
        "Stop": ["SessionEnd", "AfterAgent"],
        "Notification": ["Notification"],
        "PreCompact": ["PreCompress"]
    }

    # Matchers for Gemini events
    MATCHERS = {
        "SessionStart": "startup",
        "SessionEnd": "exit|logout",
    }

    # Generate Gemini hooks config
    gemini_hooks = {}
    
    for claude_event, gemini_events in CLAUDE_TO_GEMINI.items():
        if claude_event not in claude_hooks:
            continue
            
        # Get the first hook definition (usually only one router hook)
        claude_def = claude_hooks[claude_event][0]
        # Get the inner hook details
        inner_hook = claude_def.get("hooks", [{}])[0]
        timeout = inner_hook.get("timeout", 5000)
        
        for gemini_event in gemini_events:
            matcher = MATCHERS.get(gemini_event, "*")
            
            hook_entry = {
                "matcher": matcher,
                "hooks": [{
                    "name": "aops-router",
                    "type": "command",
                    # Point to the packaged hooks in dist/hooks
                    "command": f"AOPS={aops_path} AOPS_SESSIONS={aops_path}/.gemini/sessions python3 {dist_dir}/hooks/gemini/router.py {gemini_event}",
                    "timeout": timeout
                }]
            }
            
            if gemini_event not in gemini_hooks:
                gemini_hooks[gemini_event] = []
            gemini_hooks[gemini_event].append(hook_entry)

    # Convert commands to TOML
    commands_dist_dir = os.path.join(dist_dir, "commands")
    if os.path.exists(commands_dist_dir):
        import shutil
        shutil.rmtree(commands_dist_dir)
    os.makedirs(commands_dist_dir, exist_ok=True)

    # Run the conversion script
    convert_script = os.path.join(aops_path, "scripts", "convert_commands_to_toml.py")
    if os.path.exists(convert_script):
        import subprocess
        print("Converting commands to TOML...")
        try:
            # We want to convert commands from aops-core/commands to dist/commands
            # The script defaults to config/gemini/commands, so we need to override output
            subprocess.run(
                [sys.executable, convert_script, "--output-dir", commands_dist_dir],
                check=True,
                env={**os.environ, "AOPS": aops_path}
            )
            print(f"✓ Converted commands to {commands_dist_dir}")
        except subprocess.CalledProcessError as e:
            print(f"⚠ Failed to convert commands: {e}")
    else:
        print(f"⚠ Conversion script not found: {convert_script}")

    # Extension Manifest
    manifest = {
        "name": "aops-core",
        "version": "0.1.0",
        "description": "AcademicOps Core Framework Extension for Gemini CLI",
        "mcpServers": {
            "task_manager": {
                "command": "uv",
                "args": [
                    "run",
                    "--directory",
                    plugin_root,
                    "python",
                    "mcp_servers/tasks_server.py"
                ],
                "env": {
                    "AOPS": aops_path,
                    "ACA_DATA": aca_data_path
                }
            }
        },
        "hooks": gemini_hooks
    }

    # Write manifest
    manifest_path = os.path.join(dist_dir, "gemini-extension.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"✓ Created Gemini Extension Manifest: {manifest_path}")

if __name__ == "__main__":
    main()