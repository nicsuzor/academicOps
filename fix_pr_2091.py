import urllib.request
import json
import os

token = os.environ.get("GITHUB_TOKEN")
repo = "nicsuzor/academicOps"
pr_num = 2091

url = f"https://api.github.com/repos/{repo}/pulls/{pr_num}"
req = urllib.request.Request(url)
if token:
    req.add_header("Authorization", f"Bearer {token}")
req.add_header("Accept", "application/vnd.github.v3+json")

try:
    with urllib.request.urlopen(req) as response:
        pr = json.loads(response.read().decode())
        print(f"PR branch: {pr['head']['ref']}")
        print(f"PR repo: {pr['head']['repo']['full_name']}")
except Exception as e:
    print(f"Error fetching PR info: {e}")
