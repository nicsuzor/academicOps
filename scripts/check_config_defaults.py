#!/usr/bin/env python3
"""Detect .get() calls with defaults on configuration objects.

This pre-commit hook enforces the NO DEFAULTS fail-fast philosophy by detecting
dict.get() calls with default values on configuration-like objects.

Why this matters:
- Silent defaults hide misconfiguration for months
- Research data can be corrupted without any errors
- Violates fail-fast philosophy critical for academic integrity

Usage:
    python check_config_defaults.py file1.py file2.py ...
"""
import ast
import sys
from pathlib import Path


class ConfigDefaultFinder(ast.NodeVisitor):
    """Find .get() calls with default values on config-like objects."""

    def __init__(self):
        self.violations = []
        # Object names that represent configuration
        # Expand this list as patterns emerge
        self.config_objects = {
            'kwargs',
            'parameters',
            'config',
            'settings',
            'params',
            'options',
            'self.parameters',
            'self.config',
            'self.settings',
            'ctx.parameters',
        }

    def visit_Call(self, node):
        """Visit all function call nodes in the AST."""
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'get':
            # Check if called on a config-like object
            obj_name = ast.unparse(node.func.value)

            # Check if this is a configuration object
            is_config = any(config in obj_name.lower() for config in self.config_objects)

            if is_config:
                # Check if it has a default (2nd positional arg or 'default' kwarg)
                has_default = (
                    len(node.args) >= 2 or
                    any(kw.arg == 'default' for kw in node.keywords)
                )

                if has_default:
                    # Extract default value for display
                    if len(node.args) >= 2:
                        default_val = ast.unparse(node.args[1])
                    else:
                        default_kw = next(kw for kw in node.keywords if kw.arg == 'default')
                        default_val = ast.unparse(default_kw.value)

                    # Extract key
                    key = ast.unparse(node.args[0]) if node.args else "unknown"

                    self.violations.append({
                        'line': node.lineno,
                        'col': node.col_offset,
                        'object': obj_name,
                        'key': key,
                        'default': default_val,
                        'call': ast.unparse(node)
                    })

        # Continue visiting child nodes
        self.generic_visit(node)


def check_file(filepath: Path) -> int:
    """Check a Python file for configuration default violations.

    Args:
        filepath: Path to Python file to check

    Returns:
        0 if no violations found, 1 if violations found
    """
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=str(filepath))

        finder = ConfigDefaultFinder()
        finder.visit(tree)

        if finder.violations:
            print(f"\n{'='*80}")
            print(f"ERROR: Configuration defaults found in {filepath}")
            print(f"{'='*80}")
            print("\nConfiguration parameters must be REQUIRED, not optional with defaults.")
            print("This violates the NO DEFAULTS, FAIL-FAST core axiom.\n")

            for v in finder.violations:
                print(f"  {filepath}:{v['line']}:{v['col']}")
                print(f"    {v['object']}.get({v['key']}, {v['default']})")
                print()

            print("Fix by using one of these patterns:")
            print()
            print("  1. Pydantic Field() with no default (PREFERRED):")
            print("     class Config(BaseModel):")
            print("         param: int  # Raises ValidationError if missing")
            print()
            print("  2. Explicit check with KeyError:")
            print("     if 'param' not in config:")
            print("         raise ValueError('param must be explicitly set')")
            print("     value = config['param']")
            print()
            print("  3. Property with validation:")
            print("     @property")
            print("     def param(self) -> int:")
            print("         if 'param' not in self.parameters:")
            print("             raise ValueError('param required')")
            print("         return self.parameters['param']")
            print()
            print("See: https://github.com/nicsuzor/academicOps/issues/100")
            print(f"{'='*80}\n")
            return 1

        return 0

    except SyntaxError as e:
        print(f"ERROR: Syntax error in {filepath}: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: Failed to check {filepath}: {e}")
        return 1


def main() -> int:
    """Main entry point for pre-commit hook."""
    if len(sys.argv) < 2:
        print("Usage: check_config_defaults.py file1.py file2.py ...")
        return 0

    exit_code = 0
    checked_files = 0

    for arg in sys.argv[1:]:
        filepath = Path(arg)
        if filepath.suffix == '.py' and filepath.exists():
            exit_code |= check_file(filepath)
            checked_files += 1

    if exit_code == 0 and checked_files > 0:
        print(f"✓ No configuration defaults found in {checked_files} file(s)")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
