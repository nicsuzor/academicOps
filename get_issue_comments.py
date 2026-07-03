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

comments = get_json(f"https://api.github.com/repos/{repo}/issues/{pr_num}/comments")
if comments:
    for c in comments:
        print(f"\n--- [{c['user']['login']}] ---")
        print(c['body'])
