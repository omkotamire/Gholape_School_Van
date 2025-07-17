import os
import base64
import requests

# Set these in Streamlit secrets or pass as parameters
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or "your-token"
GITHUB_REPO = "yourusername/yourrepo"
GITHUB_BRANCH = "main"

def get_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

def get_github_file_sha(repo, branch, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    response = requests.get(url, headers=get_headers())
    if response.status_code == 200:
        return response.json().get("sha")
    return None

def push_file_to_github(local_path, github_path):
    if not os.path.exists(local_path):
        return False

    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    sha = get_github_file_sha(GITHUB_REPO, GITHUB_BRANCH, github_path)

    payload = {
        "message": f"Update {github_path}",
        "content": content,
        "branch": GITHUB_BRANCH,
    }

    if sha:
        payload["sha"] = sha  # Required for update

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{github_path}"
    r = requests.put(url, headers=get_headers(), json=payload)
    return r.status_code in [200, 201]

def restore_file_from_github(github_path, local_path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{github_path}?ref={GITHUB_BRANCH}"
    response = requests.get(url, headers=get_headers())

    if response.status_code == 200:
        content = response.json()["content"]
        decoded = base64.b64decode(content)
        with open(local_path, "wb") as f:
            f.write(decoded)
        return True
    return False