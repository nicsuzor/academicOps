"""Unit tests for .markdownlint-rules/no-horizontal-rules.js (H39)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RULE_FILE = REPO_ROOT / ".markdownlint-rules" / "no-horizontal-rules.js"


def test_rule_file_exists():
    assert RULE_FILE.is_file(), f"Expected rule file at {RULE_FILE}"


def test_rule_metadata_and_execution_via_node():
    """Execute the rule function with mock tokens via node to verify H39 triggers on hr."""
    node_script = f"""
    const rule = require('{RULE_FILE}');
    
    // Check metadata
    if (!rule.names.includes('no-horizontal-rules') || !rule.names.includes('H39')) {{
        process.stderr.write('Missing rule names\\n');
        process.exit(1);
    }}
    if (rule.parser !== 'markdownit') {{
        process.stderr.write('Wrong parser\\n');
        process.exit(2);
    }}
    
    // Test 1: hr token triggers onError
    const errors = [];
    const onError = (err) => errors.push(err);
    const paramsWithHr = {{
        parsers: {{
            markdownit: {{
                tokens: [
                    {{ type: 'heading_open', lineNumber: 1, line: '# Title' }},
                    {{ type: 'hr', lineNumber: 5, line: '---' }},
                    {{ type: 'paragraph_open', lineNumber: 7, line: 'Text' }}
                ]
            }}
        }}
    }};
    rule.function(paramsWithHr, onError);
    if (errors.length !== 1 || errors[0].lineNumber !== 5 || !errors[0].fixInfo || errors[0].fixInfo.deleteCount !== -1) {{
        process.stderr.write('Failed to detect hr token correctly or missing fixInfo\\n');
        process.exit(3);
    }}
    
    // Test 2: no hr tokens produces 0 errors
    const errorsClean = [];
    const paramsClean = {{
        parsers: {{
            markdownit: {{
                tokens: [
                    {{ type: 'heading_open', lineNumber: 1, line: '# Title' }},
                    {{ type: 'paragraph_open', lineNumber: 3, line: 'Text' }}
                ]
            }}
        }}
    }};
    rule.function(paramsClean, (err) => errorsClean.push(err));
    if (errorsClean.length !== 0) {{
        process.stderr.write('False positive on clean tokens\\n');
        process.exit(4);
    }}

    console.log(JSON.stringify({{ status: 'ok', errorsDetected: errors.length }}));
    """
    res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True)
    assert res.returncode == 0, f"Node script failed: {res.stderr}"
    data = json.loads(res.stdout.strip())
    assert data["status"] == "ok"
    assert data["errorsDetected"] == 1
