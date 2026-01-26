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

    # Hook command template
    def hook_command(event_name, timeout=5000):
        return {
            "name": "aops-router",
            "type": "command",
            "command": f"AOPS={aops_path} AOPS_SESSIONS={aops_path}/.gemini/sessions python3 {plugin_root}/hooks/gemini/router.py {event_name}",
            "timeout": timeout
        }

    # Extension Manifest
    manifest = {
        "name": "academic-ops-core",
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
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup",
                    "hooks": [hook_command("SessionStart", 15000)]
                }
            ],
            "BeforeAgent": [
                {
                    "matcher": "*",
                    "hooks": [hook_command("BeforeAgent", 20000)]
                }
            ],
            "BeforeTool": [
                {
                    "matcher": "*",
                    "hooks": [hook_command("BeforeTool", 5000)]
                }
            ],
            "AfterTool": [
                {
                    "matcher": "*",
                    "hooks": [hook_command("AfterTool", 55000)]
                }
            ],
            "SessionEnd": [
                {
                    "matcher": "exit|logout",
                    "hooks": [hook_command("SessionEnd", 5000)]
                }
            ],
            # Additional Gemini hooks
            "Notification": [
                {
                    "matcher": "*",
                    "hooks": [hook_command("Notification", 5000)]
                }
            ],
            "BeforeModel": [
                {
                    "matcher": "*",
                    "hooks": [hook_command("BeforeModel", 5000)]
                }
            ],
            "AfterModel": [
                {
                    "matcher": "*",
                    "hooks": [hook_command("AfterModel", 5000)]
                }
            ],
            "BeforeToolSelection": [
                {
                    "matcher": "*",
                    "hooks": [hook_command("BeforeToolSelection", 5000)]
                }
            ],
             "PreCompress": [
                {
                    "matcher": "*",
                    "hooks": [hook_command("PreCompress", 5000)]
                }
            ]
        }
    }

    # Write manifest
    manifest_path = os.path.join(plugin_root, "gemini-extension.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"✓ Created Gemini Extension Manifest: {manifest_path}")

if __name__ == "__main__":
    main()