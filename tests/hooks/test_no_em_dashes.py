"""Unit tests for .markdownlint-rules/no-em-dashes.js."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RULE_FILE = REPO_ROOT / ".markdownlint-rules" / "no-em-dashes.js"


def test_rule_file_exists():
    assert RULE_FILE.is_file(), f"Expected rule file at {RULE_FILE}"


def test_rule_metadata_and_execution_via_node():
    """Execute the rule function via node to verify em-dash detection and fixInfo."""
    node_script = f"""
    const rule = require('{RULE_FILE}');
    
    // Check metadata
    if (!rule.names.includes('no-em-dashes') || !rule.names.includes('no-em-dash')) {{
        process.stderr.write('Missing rule names\\n');
        process.exit(1);
    }}
    if (rule.parser !== 'none') {{
        process.stderr.write('Wrong parser\\n');
        process.exit(2);
    }}
    
    // Test 1: em-dash triggers onError with correct line, column, and fixInfo
    const errors = [];
    const onError = (err) => errors.push(err);
    const paramsWithEmDash = {{
        lines: [
            '# Title without dashes',
            'Some text — with an em-dash',
            'Another line with — two — em-dashes'
        ]
    }};
    rule.function(paramsWithEmDash, onError);
    if (errors.length !== 3) {{
        process.stderr.write(`Expected 3 errors, got ${{errors.length}}\\n`);
        process.exit(3);
    }}
    if (errors[0].lineNumber !== 2 || !errors[0].fixInfo || errors[0].fixInfo.insertText !== '--') {{
        process.stderr.write('Failed to configure fixInfo correctly on first error\\n');
        process.exit(4);
    }}
    if (errors[1].lineNumber !== 3 || errors[2].lineNumber !== 3) {{
        process.stderr.write('Failed to detect multiple errors on same line\\n');
        process.exit(5);
    }}
    
    // Test 2: clean lines produce 0 errors
    const errorsClean = [];
    const paramsClean = {{
        lines: [
            '# Title without dashes',
            'Some text -- with double hyphens',
            'Normal sentence.'
        ]
    }};
    rule.function(paramsClean, (err) => errorsClean.push(err));
    if (errorsClean.length !== 0) {{
        process.stderr.write('False positive on clean lines\\n');
        process.exit(6);
    }}

    console.log(JSON.stringify({{ status: 'ok', errorsDetected: errors.length }}));
    """
    res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True)
    assert res.returncode == 0, f"Node script failed: {res.stderr}"
    data = json.loads(res.stdout.strip())
    assert data["status"] == "ok"
    assert data["errorsDetected"] == 3
