#!/usr/bin/env python3
import json
import sys

def main():
    # Example hook that just passes the event through.
    # Read the hook context from stdin (provided by the agent framework)
    try:
        input_data = sys.stdin.read()
        if not input_data:
            sys.exit(0)
            
        event = json.loads(input_data)
        
        # In a real hook, you could inspect or mutate the event here.
        # For example, intercepting a tool call or changing a message.
        
        # Write the resulting event back to stdout
        print(json.dumps(event))
        
    except Exception as e:
        # Write errors to stderr so they don't corrupt the hook JSON output
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
