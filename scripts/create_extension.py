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
                    "hooks": [
                        {
                            "name": "aops-router",
                            "type": "command",
                            "command": f"AOPS={aops_path} AOPS_SESSIONS={aops_path}/.gemini/sessions python3 {plugin_root}/hooks/gemini/router.py SessionStart",
                            "timeout": 15000
                        }
                    ]
                }
            ],
            "BeforeAgent": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "name": "aops-router",
                            "type": "command",
                            "command": f"AOPS={aops_path} AOPS_SESSIONS={aops_path}/.gemini/sessions python3 {plugin_root}/hooks/gemini/router.py BeforeAgent",
                            "timeout": 20000
                        }
                    ]
                }
            ],
            "BeforeTool": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "name": "aops-router",
                            "type": "command",
                            "command": f"AOPS={aops_path} AOPS_SESSIONS={aops_path}/.gemini/sessions python3 {plugin_root}/hooks/gemini/router.py BeforeTool",
                            "timeout": 5000
                        }
                    ]
                }
            ],
            "AfterTool": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "name": "aops-router",
                            "type": "command",
                            "command": f"AOPS={aops_path} AOPS_SESSIONS={aops_path}/.gemini/sessions python3 {plugin_root}/hooks/gemini/router.py AfterTool",
                            "timeout": 55000
                        }
                    ]
                }
            ],
            "SessionEnd": [
                {
                    "matcher": "exit|logout",
                    "hooks": [
                        {
                            "name": "aops-router",
                            "type": "command",
                            "command": f"AOPS={aops_path} AOPS_SESSIONS={aops_path}/.gemini/sessions python3 {plugin_root}/hooks/gemini/router.py SessionEnd",
                            "timeout": 5000
                        }
                    ]
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
