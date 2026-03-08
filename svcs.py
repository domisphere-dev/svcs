import os
import sys
import json
import hashlib
import time
import fnmatch
from pathlib import Path
import base64

try:
    import requests
except ImportError:
    requests = None

SVCS_DIR = ".svcs"
OBJECTS = f"{SVCS_DIR}/objects"
COMMITS = f"{SVCS_DIR}/commits"
BRANCHES = f"{SVCS_DIR}/branches"
INDEX = f"{SVCS_DIR}/index.json"
HEAD = f"{SVCS_DIR}/HEAD"
IGNORE_FILE = ".svcsignore"
REMOTES = f"{SVCS_DIR}/remotes.json"

def die(msg, code=1):
    print(msg)
    sys.exit(code)

def ensure_repo():
    if not os.path.exists(SVCS_DIR):
        die("Not an SVCS repo! Did you forget to run `svcs init`?", 1)

def ensure_requests():
    if not requests:
        die("requests module required for push/pull/clone (pip install requests)")

def normalize_base_url(url: str) -> str:
    return url.rstrip("/")

def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()

def read_json(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)

def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def current_branch():
    with open(HEAD) as f:
        return f.read().strip()

def branch_head(branch):
    path = f"{BRANCHES}/{branch}"
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return f.read().strip()

def set_branch_head(branch, commit):
    with open(f"{BRANCHES}/{branch}", "w") as f:
        f.write(commit)

def commit_path(commit_id: str) -> str:
    return f"{COMMITS}/{commit_id}.json"

def commit_exists(commit_id: str) -> bool:
    return os.path.exists(commit_path(commit_id))

# Ignore handling
def load_ignore():
    patterns = []
    if os.path.exists(IGNORE_FILE):
        with open(IGNORE_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    patterns.append(".svcs/")
    return patterns

def is_ignored(path, patterns):
    for pattern in patterns:
        if pattern.endswith("/"):
            if path.startswith(pattern):
                return True
        if fnmatch.fnmatch(path, pattern):
            return True
    return False

def get_all_files():
    patterns = load_ignore()
    files = []
    for root, dirs, filenames in os.walk("."):
        if root.startswith(f"./{SVCS_DIR}"):
            continue
        for name in filenames:
            path = os.path.join(root, name)
            path = os.path.relpath(path, ".")
            if is_ignored(path, patterns):
                continue
            files.append(path)
    return files

# Core SVCS ops
def init():
    os.makedirs(OBJECTS, exist_ok=True)
    os.makedirs(COMMITS, exist_ok=True)
    os.makedirs(BRANCHES, exist_ok=True)
    write_json(INDEX, {})
    write_json(REMOTES, {})
    with open(HEAD, "w") as f:
        f.write("main")
    set_branch_head("main", "")
    print("SVCS repo initialized!")

def add(target):
    ensure_repo()
    if not target:
        die("usage: svcs add <file|.>", 2)

    index = read_json(INDEX)
    files = get_all_files() if target == "." else [target]

    added_any = False
    for file in files:
        if not os.path.exists(file):
            print(f"warning: '{file}' does not exist, skipping")
            continue
        with open(file, "rb") as f:
            data = f.read()
        h = sha1(data)
        obj_path = f"{OBJECTS}/{h}"
        if not os.path.exists(obj_path):
            with open(obj_path, "wb") as f:
                f.write(data)
        index[file] = h
        added_any = True
        print(f"added {file}")

    if not added_any:
        print("nothing added")
    write_json(INDEX, index)

def commit(message):
    ensure_repo()
    if not message:
        die("usage: svcs commit <message>", 2)

    index = read_json(INDEX)
    if not index:
        die("nothing to commit (index is empty). Run svcs add ... first.", 1)

    branch = current_branch()
    parent = branch_head(branch)

    payload = json.dumps(index, sort_keys=True).encode()
    commit_id = sha1(payload + str(time.time()).encode())[:7]

    commit_data = {
        "message": message,
        "timestamp": time.time(),
        "files": index,
        "parent": parent,
        "branch": branch
    }

    write_json(commit_path(commit_id), commit_data)
    set_branch_head(branch, commit_id)
    print(f"commit {commit_id} - {message}")

# Remotes now store url+repo
def remote_add(name, url, repo):
    ensure_repo()
    if not name or not url or not repo:
        die("usage: svcs remote add <name> <url> <repo>", 2)

    remotes = read_json(REMOTES)
    remotes[name] = {"url": normalize_base_url(url), "repo": repo}
    write_json(REMOTES, remotes)
    print(f"remote {name} added -> {url} (repo={repo})")

def _get_remote(remote_name):
    remotes = read_json(REMOTES)
    if remote_name not in remotes:
        die(f"remote {remote_name} not found")
    remote = remotes[remote_name]
    if not isinstance(remote, dict) or "url" not in remote or "repo" not in remote:
        die(f"remote {remote_name} invalid. Re-add it with: svcs remote add {remote_name} <url> <repo>")
    return remote

def _gather_reachable_objects_and_commits(commit_id):
    objects_to_send = {}
    commits_to_send = {}
    visited = set()

    def gather(cid):
        if not cid or cid in visited:
            return
        visited.add(cid)
        data = read_json(commit_path(cid))
        if not data:
            return
        commits_to_send[cid] = data
        for _, h in data["files"].items():
            obj_file = f"{OBJECTS}/{h}"
            if os.path.exists(obj_file):
                with open(obj_file, "rb") as fobj:
                    objects_to_send[h] = base64.b64encode(fobj.read()).decode()
        gather(data.get("parent"))

    gather(commit_id)
    return objects_to_send, commits_to_send

def _build_working_tree_snapshot():
    # Upload all non-ignored files from working dir (NOT .svcs)
    snapshot = {}
    for path in get_all_files():
        if not os.path.exists(path) or not os.path.isfile(path):
            continue
        with open(path, "rb") as f:
            snapshot[path] = base64.b64encode(f.read()).decode()
    return snapshot

def _write_working_tree_snapshot(snapshot):
    # Write files to working directory (respecting paths)
    for relpath, b64 in snapshot.items():
        # Safety: never write into .svcs from snapshot
        if relpath.startswith(".svcs/") or relpath == ".svcs":
            continue
        data = base64.b64decode(b64)
        Path(os.path.dirname(relpath) or ".").mkdir(parents=True, exist_ok=True)
        with open(relpath, "wb") as f:
            f.write(data)

def push(remote_name, branch_name=None, auto_create=True):
    ensure_repo()
    ensure_requests()

    remote = _get_remote(remote_name)
    branch = branch_name or current_branch()
    commit_id = branch_head(branch)
    if not commit_id:
        die(f"branch {branch} has no commits to push")

    objects_to_send, commits_to_send = _gather_reachable_objects_and_commits(commit_id)

    # NEW: include working tree snapshot (everything not ignored by .svcsignore)
    working_tree = _build_working_tree_snapshot()

    payload = {
        "objects": objects_to_send,
        "commits": commits_to_send,
        "branches": {branch: commit_id},
        "working_tree": working_tree,
        "snapshot_commit": commit_id,
    }

    r = requests.post(f"{remote['url']}/push/{remote['repo']}", json=payload)
    if r.status_code == 200:
        print(f"pushed {branch} -> {remote_name}/{remote['repo']} (including working tree)")
        return

    if r.status_code == 404 and auto_create:
        c = requests.post(f"{remote['url']}/create/{remote['repo']}")
        if c.status_code not in (201, 400):
            die(f"push failed: remote create failed ({c.status_code}): {c.text}")
        r2 = requests.post(f"{remote['url']}/push/{remote['repo']}", json=payload)
        if r2.status_code == 200:
            print(f"pushed {branch} -> {remote_name}/{remote['repo']} (after create, including working tree)")
            return
        die(f"push failed after create ({r2.status_code}): {r2.text}")

    die(f"push failed ({r.status_code}): {r.text}")

def pull(remote_name):
    # IMPORTANT: pull only updates .svcs (objects/commits/branches); does NOT touch working files.
    ensure_repo()
    ensure_requests()

    remote = _get_remote(remote_name)
    r = requests.get(f"{remote['url']}/pull/{remote['repo']}")
    if r.status_code != 200:
        die(f"pull failed ({r.status_code}): {r.text}")

    data = r.json()

    for h, b64 in data.get("objects", {}).items():
        obj_file = f"{OBJECTS}/{h}"
        if not os.path.exists(obj_file):
            with open(obj_file, "wb") as f:
                f.write(base64.b64decode(b64))

    for cid, commit_data in data.get("commits", {}).items():
        path = commit_path(cid)
        if not os.path.exists(path):
            write_json(path, commit_data)

    for br, head in data.get("branches", {}).items():
        set_branch_head(br, head)

    print(f"pulled .svcs data from {remote_name}/{remote['repo']}")

def clone(url, repo, folder, branch="main"):
    # Clone pulls .svcs + full working tree snapshot
    ensure_requests()
    if os.path.exists(folder):
        die(f"folder {folder} already exists")

    os.makedirs(folder)
    os.chdir(folder)

    init()
    remote_add("origin", url, repo)

    # pull only .svcs db
    pull("origin")

    # find commit to snapshot (branch head)
    head_commit = branch_head(branch)
    if not head_commit:
        print("clone: remote has no commits yet; cloned empty repo")
        return

    # fetch snapshot for that commit and write files
    remote_cfg = _get_remote("origin")
    r = requests.get(f"{remote_cfg['url']}/snapshot/{remote_cfg['repo']}/{head_commit}")
    if r.status_code != 200:
        die(f"clone failed to fetch snapshot for commit {head_commit} ({r.status_code}): {r.text}")

    snapshot = r.json()
    _write_working_tree_snapshot(snapshot)
    print(f"cloned {url} (repo={repo}) into {folder} at {branch}@{head_commit}")

def usage():
    print(
        "svcs <command>\n\n"
        "commands:\n"
        "  init\n"
        "  add <file|.>\n"
        "  commit <message>\n"
        "  remote add <name> <url> <repo>\n"
        "  push <remote> [branch]\n"
        "  pull <remote>\n"
        "  clone <url> <repo> <folder>\n"
    )

def main():
    if len(sys.argv) < 2:
        usage()
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "init":
        init()
    elif cmd == "add":
        add(args[0] if args else None)
    elif cmd == "commit":
        commit(args[0] if args else None)
    elif cmd == "remote":
        if len(args) < 1 or args[0] != "add" or len(args) != 4:
            die("usage: svcs remote add <name> <url> <repo>", 2)
        remote_add(args[1], args[2], args[3])
    elif cmd == "push":
        if len(args) < 1:
            die("usage: svcs push <remote> [branch]", 2)
        push(args[0], args[1] if len(args) > 1 else None)
    elif cmd == "pull":
        if len(args) != 1:
            die("usage: svcs pull <remote>", 2)
        pull(args[0])
    elif cmd == "clone":
        if len(args) != 3:
            die("usage: svcs clone <url> <repo> <folder>", 2)
        clone(args[0], args[1], args[2])
    else:
        die("unknown command", 2)

if __name__ == "__main__":
    main()