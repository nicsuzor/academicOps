import json
import os
import urllib.request

token = os.environ.get("GITHUB_TOKEN")
repo = "nicsuzor/academicOps"


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


prs = get_json(f"https://api.github.com/repos/{repo}/pulls?state=open")
if prs:
    for pr in prs:
        num = pr["number"]
        title = pr["title"]
        print(f"\n--- PR #{num}: {title} ---")

        # Get checks
        sha = pr["head"]["sha"]
        checks = get_json(f"https://api.github.com/repos/{repo}/commits/{sha}/check-runs")
        if checks and "check_runs" in checks:
            failed_checks = [c for c in checks["check_runs"] if c["conclusion"] == "failure"]
            if failed_checks:
                print("Failed checks:")
                for c in failed_checks:
                    print(f"  - {c['name']} (URL: {c['html_url']})")
            else:
                print("No failed checks.")

        # Get comments
        comments = get_json(f"https://api.github.com/repos/{repo}/issues/{num}/comments")
        if comments:
            print("Recent comments:")
            for c in comments[-3:]:
                print(f"  [{c['user']['login']}] {c['body'][:100]}...")
