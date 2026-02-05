import json
import os
import sys
import shutil
import subprocess

# Helper to convert MCP server config (simplified from convert_mcp_to_gemini.py)
def convert_mcp_config(claude_servers):
    gemini_servers = {}
    for name, config in claude_servers.items():
        server_type = config.get("type", "stdio")
        converted = {}
        if server_type == "http":
            if "url" in config:
                converted["url"] = config["url"]
                if "headers" in config:
                    converted["headers"] = config["headers"]
        elif server_type == "stdio":
            if "command" in config:
                converted["command"] = config["command"]
                if "args" in config:
                    converted["args"] = config["args"]
                if "env" in config:
                    converted["env"] = config["env"]
        
        if converted:
            gemini_servers[name] = converted
    return gemini_servers

def main():
    aops_path = os.environ.get("AOPS")
    aca_data_path = os.environ.get("ACA_DATA")
    
    if not aops_path or not aca_data_path:
        print("Error: AOPS and ACA_DATA environment variables must be set.")
        sys.exit(1)

    plugin_root = os.path.join(aops_path, "aops-core")
    dist_root = os.path.join(aops_path, "dist")
    
    # ---------------------------------------------------------
    # 1. Setup Dist Directories
    # ---------------------------------------------------------
    core_dist = os.path.join(dist_root, "aops-core")
    tools_dist = os.path.join(dist_root, "aops-tools")
    
    # Clean up old root files if they exist to avoid confusion
    for item in os.listdir(dist_root):
        item_path = os.path.join(dist_root, item)
        if item_path not in [core_dist, tools_dist]:
            if os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
    
    for d in [core_dist, tools_dist]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)

    # ---------------------------------------------------------
    # 2. Build aops-core
    # ---------------------------------------------------------
    print("Building aops-core...")
    
    # Symlinks
    for item in ["skills", "GEMINI.md"]:
        src = os.path.join(plugin_root, item)
        dst = os.path.join(core_dist, item)
        if os.path.exists(src):
            os.symlink(src, dst)

    # Hooks (Selective)
    hooks_src = os.path.join(plugin_root, "hooks")
    hooks_dst = os.path.join(core_dist, "hooks")
    os.makedirs(hooks_dst, exist_ok=True)
    if os.path.exists(hooks_src):
        for item in os.listdir(hooks_src):
            if item == "hooks.json":
                continue
            os.symlink(os.path.join(hooks_src, item), os.path.join(hooks_dst, item))

    # Hooks Config Generation
    hooks_json_path = os.path.join(hooks_src, "hooks.json")
    claude_hooks = {}
    if os.path.exists(hooks_json_path):
        with open(hooks_json_path, "r") as f:
            claude_hooks = json.load(f).get("hooks", {})

    CLAUDE_TO_GEMINI = {
        "SessionStart": ["SessionStart"],
        "PreToolUse": ["BeforeTool"],
        "PostToolUse": ["AfterTool"],
        "UserPromptSubmit": ["BeforeAgent"],
        "Stop": ["SessionEnd", "AfterAgent"],
        "Notification": ["Notification"],
        "PreCompact": ["PreCompress"]
    }
    MATCHERS = {"SessionStart": "startup", "SessionEnd": "exit|logout"}

    gemini_hooks = {}
    for c_event, g_events in CLAUDE_TO_GEMINI.items():
        if c_event in claude_hooks:
            timeout = claude_hooks[c_event][0].get("hooks", [{}])[0].get("timeout", 5000)
            for g_event in g_events:
                matcher = MATCHERS.get(g_event, "*")
                if g_event not in gemini_hooks:
                    gemini_hooks[g_event] = []
                gemini_hooks[g_event].append({
                    "matcher": matcher,
                    "hooks": [{
                        "name": "aops-router",
                        "type": "command",
                        "command": f"AOPS={aops_path} AOPS_SESSIONS={aops_path}/.gemini/sessions python3 {core_dist}/hooks/router.py --client gemini {g_event}",
                        "timeout": timeout
                    }]
                })

    # MCP Servers for Core
    core_mcp_path = os.path.join(plugin_root, ".mcp.json")
    core_mcps = {}
    if os.path.exists(core_mcp_path):
        with open(core_mcp_path) as f:
            core_mcps = convert_mcp_config(json.load(f).get("mcpServers", {}))
    
    # Ensure task_manager is present and correct
    core_mcps["task_manager"] = {
        "command": "uv",
        "args": ["run", "--directory", plugin_root, "python", "mcp_servers/tasks_server.py"],
        "env": {"AOPS": aops_path, "ACA_DATA": aca_data_path}
    }

    # Manifest Core
    with open(os.path.join(core_dist, "gemini-extension.json"), "w") as f:
        json.dump({
            "name": "aops-core",
            "version": "0.1.0",
            "description": "AcademicOps Core Framework",
            "mcpServers": core_mcps
        }, f, indent=2)

    # Write hooks to hooks/hooks.json
    with open(os.path.join(hooks_dst, "hooks.json"), "w") as f:
        json.dump({
            "hooks": gemini_hooks
        }, f, indent=2)

    # Commands (All go to core)
    commands_dist = os.path.join(core_dist, "commands")
    convert_script = os.path.join(aops_path, "scripts", "convert_commands_to_toml.py")
    if os.path.exists(convert_script):
        subprocess.run([sys.executable, convert_script, "--output-dir", commands_dist], env={**os.environ, "AOPS": aops_path})

    # ---------------------------------------------------------
    # 3. Build aops-tools
    # ---------------------------------------------------------
    print("Building aops-tools...")
    tools_src_root = os.path.join(aops_path, "aops-tools")
    
    # Symlinks
    for item in ["skills"]:
        src = os.path.join(tools_src_root, item)
        dst = os.path.join(tools_dist, item)
        if os.path.exists(src):
            os.symlink(src, dst)

    # MCP Servers for Tools
    tools_mcp_path = os.path.join(tools_src_root, ".mcp.json")
    tools_mcps = {}
    if os.path.exists(tools_mcp_path):
        with open(tools_mcp_path) as f:
            tools_mcps = convert_mcp_config(json.load(f).get("mcpServers", {}))

    # Remove task_manager from tools if present (handled in core)
    if "task_manager" in tools_mcps:
        del tools_mcps["task_manager"]

    # Manifest Tools
    with open(os.path.join(tools_dist, "gemini-extension.json"), "w") as f:
        json.dump({
            "name": "aops-tools",
            "version": "0.1.0",
            "description": "AcademicOps Tools",
            "mcpServers": tools_mcps
        }, f, indent=2)

    print("✓ Extensions created in dist/aops-core and dist/aops-tools")

if __name__ == "__main__":
    main()