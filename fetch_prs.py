import json
import os
import urllib.request

token = os.environ.get("GITHUB_TOKEN")
repo = "nicsuzor/academicOps"
url = f"https://api.github.com/repos/{repo}/pulls?state=open"

req = urllib.request.Request(url)
if token:
    req.add_header("Authorization", f"Bearer {token}")
req.add_header("Accept", "application/vnd.github.v3+json")

try:
    with urllib.request.urlopen(req) as response:
        prs = json.loads(response.read().decode())
        for pr in prs:
            print(f"PR #{pr['number']}: {pr['title']} (user: {pr['user']['login']})")
except Exception as e:
    print(f"Error: {e}")
