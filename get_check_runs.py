import urllib.request
import json
import os
import sys

token = os.environ.get("GITHUB_TOKEN")
repo = "nicsuzor/academicOps"
pr_num = sys.argv[1]

def get_json(url):
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

# Get PR to get SHA
pr = get_json(f"https://api.github.com/repos/{repo}/pulls/{pr_num}")
sha = pr['head']['sha']

checks = get_json(f"https://api.github.com/repos/{repo}/commits/{sha}/check-runs")
if checks and 'check_runs' in checks:
    for c in checks['check_runs']:
        if c['conclusion'] == 'failure':
            print(f"Failed: {c['name']}")
            print(f"Output: {c.get('output', {}).get('summary', 'No summary')}")
            print(f"Details: {c.get('output', {}).get('text', 'No details')}")
