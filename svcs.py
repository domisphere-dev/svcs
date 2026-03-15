import os
import sys
import json
import hashlib
import time
import fnmatch
from pathlib import Path
import base64

# Optional requests for remote functionality
try:
    import requests
except ImportError:
    requests = None

# - Paths / Config
SVCS_DIR = ".svcs"
OBJECTS = f"{SVCS_DIR}/objects"
COMMITS = f"{SVCS_DIR}/commits"
TWIGS = f"{SVCS_DIR}/twigs"
INDEX = f"{SVCS_DIR}/index.json"
HEAD = f"{SVCS_DIR}/HEAD"
IGNORE_FILE = ".svcsignore"
REMOTES_TOKEN_FILE = f"{SVCS_DIR}/remotes-token.json"
REMOTES = f"{SVCS_DIR}/remotes.json"

# - Utils
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

def current_twig():
    with open(HEAD) as f:
        return f.read().strip()

def twig_head(twig):
    path = f"{TWIGS}/{twig}"
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return f.read().strip()

def set_twig_head(twig, commit):
    with open(f"{TWIGS}/{twig}", "w") as f:
        f.write(commit)

def commit_path(commit_id: str) -> str:
    return f"{COMMITS}/{commit_id}.json"

def commit_exists(commit_id: str) -> bool:
    return os.path.exists(commit_path(commit_id))

# - Ignore handling
def load_ignore():
    patterns = []
    if os.path.exists(IGNORE_FILE):
        with open(IGNORE_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Normalize patterns so "dist/" also matches when paths don't have "./"
                    if line.startswith("./"):
                        line = line[2:]
                    line = line.replace("\\", "/")
                    patterns.append(line)

    # Always ignore SVCS internals
    patterns.append(".svcs/")
    return patterns

def is_ignored(path, patterns):
    # Normalize path into the same form as patterns:
    # - no leading "./"
    # - forward slashes
    path = path.replace("\\", "/")
    if path.startswith("./"):
        path = path[2:]

    for pattern in patterns:
        pattern = pattern.replace("\\", "/")
        if pattern.startswith("./"):
            pattern = pattern[2:]

        # If pattern endswith "/" treat it as a directory prefix ignore
        if pattern.endswith("/"):
            # match "dist/" against "dist" and "dist/..."
            prefix = pattern[:-1]
            if path == prefix or path.startswith(pattern):
                return True

        # glob match for everything else
        if fnmatch.fnmatch(path, pattern):
            return True

    return False

def get_all_files():
    patterns = load_ignore()
    files = []
    for root, dirs, filenames in os.walk("."):
        # Normalize root once so we can reliably skip .svcs
        root_norm = root.replace("\\", "/")
        if root_norm.startswith("./"):
            root_norm = root_norm[2:]

        if root_norm == SVCS_DIR or root_norm.startswith(f"{SVCS_DIR}/"):
            continue

        for name in filenames:
            path = os.path.join(root, name)
            path = os.path.relpath(path, ".")
            path = path.replace("\\", "/")
            if path.startswith("./"):
                path = path[2:]

            if is_ignored(path, patterns):
                continue
            files.append(path)
    return files

# ----------------
# Core SVCS ops
# ----------------
def init():
    os.makedirs(OBJECTS, exist_ok=True)
    os.makedirs(COMMITS, exist_ok=True)
    os.makedirs(TWIGS, exist_ok=True)
    write_json(INDEX, {})
    write_json(REMOTES, {})
    with open(HEAD, "w") as f:
        f.write("main")
    set_twig_head("main", "")
    print("SVCS repo initialized! Time to make history, literally.")

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

    twig = current_twig()
    parent = twig_head(twig)

    payload = json.dumps(index, sort_keys=True).encode()
    commit_id = sha1(payload + str(time.time()).encode())[:7]

    commit_data = {
        "message": message,
        "timestamp": time.time(),
        "files": index,
        "parent": parent,
        "twig": twig,
    }

    write_json(commit_path(commit_id), commit_data)
    set_twig_head(twig, commit_id)
    print(f"commit {commit_id} - {message} (yes, you made history)")

# ----------------
# Local commands
# ----------------
def log():
    ensure_repo()
    twig = current_twig()
    commit_id = twig_head(twig)
    if not commit_id:
        print("(no commits yet)")
        return

    while commit_id:
        data = read_json(commit_path(commit_id))
        if not data or "message" not in data:
            print(f"(commit data missing for {commit_id})")
            return
        print(f"commit {commit_id}")
        print(f"message: {data['message']}")
        print()
        commit_id = data.get("parent")

def timeline():
    ensure_repo()
    twig_name = current_twig()
    commit_id = twig_head(twig_name)
    if not commit_id:
        print("(no commits yet)")
        return

    while commit_id:
        data = read_json(commit_path(commit_id))
        if not data or "message" not in data:
            print(f"(commit data missing for {commit_id})")
            return
        print(f"* {commit_id} ({data.get('twig', '?')})")
        print(f"| {data['message']}")
        print("|")
        commit_id = data.get("parent")

def status():
    ensure_repo()
    index = read_json(INDEX)
    changed = []
    staged = list(index.keys())
    all_files = get_all_files()

    for f in all_files:
        try:
            with open(f, "rb") as file:
                h = sha1(file.read())
        except OSError:
            continue

        if f in index:
            if h != index[f]:
                changed.append(f)
        else:
            changed.append(f)

    print("- Staged files:")
    for f in staged:
        print(f"  {f}")

    print("- Modified / unstaged files:")
    for f in changed:
        if f not in staged:
            print(f"  {f}")

def diff():
    ensure_repo()
    index = read_json(INDEX)
    if not index:
        print("(nothing staged)")
        return

    for file, h in index.items():
        obj_path = f"{OBJECTS}/{h}"
        if not os.path.exists(obj_path):
            continue
        if not os.path.exists(file):
            print(f"diff for {file}: (file missing in working directory)")
            continue

        with open(file, "r", errors="ignore") as f1, open(obj_path, "r", errors="ignore") as f2:
            cur = f1.readlines()
            old = f2.readlines()
            if cur != old:
                print(f"diff for {file}:")
                for l1, l2 in zip(old, cur):
                    if l1 != l2:
                        print(f"- {l1.strip()} -> {l2.strip()}")
                if len(cur) > len(old):
                    for l in cur[len(old):]:
                        print(f"- added: {l.strip()}")
                elif len(old) > len(cur):
                    for l in old[len(cur):]:
                        print(f"- removed: {l.strip()}")

def twig(name):
    ensure_repo()
    if not name:
        die("usage: svcs twig <name>", 2)

    cur = current_twig()
    commit_id = twig_head(cur) or ""
    set_twig_head(name, commit_id)
    print(f"twig {name} created at {commit_id} (you fancy now)")

def checkout(target):
    ensure_repo()
    if not target:
        die("usage: svcs checkout <twig|commit>", 2)

    twig_path = f"{TWIGS}/{target}"
    if os.path.exists(twig_path):
        with open(HEAD, "w") as f:
            f.write(target)
        commit_id = twig_head(target)
        if commit_id:
            restore_commit(commit_id)
        print(f"Switched to twig {target}")
        return

    if not commit_exists(target):
        die(f"unknown twig or commit: {target}", 1)

    restore_commit(target)
    print(f"Checked out commit {target}")

def restore_commit(commit_id):
    if not commit_id:
        return

    path = commit_path(commit_id)
    if not os.path.exists(path):
        die(f"commit not found: {commit_id}", 1)

    data = read_json(path)
    if not data or "files" not in data:
        die(f"commit data invalid: {commit_id}", 1)

    for file_path, obj in data["files"].items():
        obj_file = f"{OBJECTS}/{obj}"
        if not os.path.exists(obj_file):
            die(f"object missing for {file_path}: {obj}", 1)

        with open(obj_file, "rb") as f:
            content = f.read()

        Path(os.path.dirname(file_path) or ".").mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(content)

def info():
    print(
        "===================================\n"
        "Simple Version System - SVCS\n"
        "Copyright (C) 2026 Dominik Hupfauer\n"
        "Version 1.1.0.0\n"
        "=====================================\n"
    )

# ----------------
# Auth/token helpers (client-side)
# ----------------
def _load_tokens_local():
    # { "<server-url>": { "<username>": "<token>" } }
    data = read_json(REMOTES_TOKEN_FILE)
    if not isinstance(data, dict):
        return {}
    return data

def _save_tokens_local(data):
    ensure_repo()
    write_json(REMOTES_TOKEN_FILE, data)

def _get_token_for(server_url: str, username: str):
    tokens = _load_tokens_local()
    server_url = normalize_base_url(server_url)
    per_server = tokens.get(server_url, {})
    if not isinstance(per_server, dict):
        return None
    tok = per_server.get(username)
    if not tok:
        return None
    return tok

def _set_token_for(server_url: str, username: str, token: str):
    tokens = _load_tokens_local()
    server_url = normalize_base_url(server_url)
    if server_url not in tokens or not isinstance(tokens.get(server_url), dict):
        tokens[server_url] = {}
    tokens[server_url][username] = token
    _save_tokens_local(tokens)

def _auth_headers(server_url: str, username: str):
    tok = _get_token_for(server_url, username)
    if not tok:
        return {}
    return {"Authorization": f"Bearer {tok}"}

# ----------------
# Remote commands
# ----------------
def remote_add(name, url, repo):
    ensure_repo()
    if not name or not url or not repo:
        die("usage: svcs remote add <name> <remote-server-url> <repo>", 2)

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
        die(f"remote {remote_name} invalid. Re-add it with: svcs remote add {remote_name} <remote-server-url> <repo>")
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
    snapshot = {}
    for path in get_all_files():
        if not os.path.exists(path) or not os.path.isfile(path):
            continue
        with open(path, "rb") as f:
            snapshot[path] = base64.b64encode(f.read()).decode()
    return snapshot

def _write_working_tree_snapshot(snapshot):
    for relpath, b64 in snapshot.items():
        if relpath.startswith(".svcs/") or relpath == ".svcs":
            continue
        data = base64.b64decode(b64)
        Path(os.path.dirname(relpath) or ".").mkdir(parents=True, exist_ok=True)
        with open(relpath, "wb") as f:
            f.write(data)

def login(server_url, username, password):
    """
    Logs in once and stores token in .svcs/remotes-token.json (per repo).
    """
    ensure_repo()
    ensure_requests()

    server_url = normalize_base_url(server_url)
    r = requests.post(
        f"{server_url}/login",
        json={"username": username, "password": password},
    )
    if r.status_code != 200:
        die(f"login failed ({r.status_code}): {r.text}")

    data = r.json()
    token = data.get("token")
    if not token:
        die("login failed: server did not return token")

    _set_token_for(server_url, username, token)
    print(f"logged in as {username} to {server_url} (token saved in {REMOTES_TOKEN_FILE})")

def push(remote_name, twig_name=None, auto_create=True, username=None):
    ensure_repo()
    ensure_requests()

    if not username:
        die("push requires --user <username> (so we know which per-user scope to use).", 2)

    remote = _get_remote(remote_name)
    twig_name = twig_name or current_twig()
    commit_id = twig_head(twig_name)
    if not commit_id:
        die(f"twig {twig_name} has no commits to push")

    objects_to_send, commits_to_send = _gather_reachable_objects_and_commits(commit_id)
    working_tree = _build_working_tree_snapshot()

    payload = {
        "objects": objects_to_send,
        "commits": commits_to_send,
        "twigs": {twig_name: commit_id},
        "working_tree": working_tree,
        "snapshot_commit": commit_id,
    }

    headers = _auth_headers(remote["url"], username)
    if not headers:
        die(f"no token found for {remote['url']} as {username}. Run: svcs login {remote['url']} {username} <password>", 1)

    url_push = f"{remote['url']}/push/{username}/{remote['repo']}"
    r = requests.post(url_push, json=payload, headers=headers)
    if r.status_code == 200:
        print(f"pushed {twig_name} -> {remote_name}/{username}/{remote['repo']} (including working tree)")
        return

    if r.status_code == 401:
        die("push failed: unauthorized (token missing/invalid). Try `svcs login ...` again.", 1)

    if r.status_code == 403:
        die("push failed: forbidden (token user does not match URL user)", 1)

    if r.status_code == 404 and auto_create:
        url_create = f"{remote['url']}/create/{username}/{remote['repo']}"
        c = requests.post(url_create, headers=headers)
        if c.status_code not in (201, 400):
            die(f"push failed: remote create failed ({c.status_code}): {c.text}")

        r2 = requests.post(url_push, json=payload, headers=headers)
        if r2.status_code == 200:
            print(f"pushed {twig_name} -> {remote_name}/{username}/{remote['repo']} (after create, including working tree)")
            return
        die(f"push failed after create ({r2.status_code}): {r2.text}")

    die(f"push failed ({r.status_code}): {r.text}")

def pull(remote_name, username=None):
    ensure_repo()
    ensure_requests()

    if not username:
        die("pull requires --user <username> (per-user scope).", 2)

    remote = _get_remote(remote_name)
    headers = _auth_headers(remote["url"], username)
    if not headers:
        die(f"no token found for {remote['url']} as {username}. Run: svcs login {remote['url']} {username} <password>", 1)

    r = requests.get(f"{remote['url']}/pull/{username}/{remote['repo']}", headers=headers)
    if r.status_code == 401:
        die("pull failed: unauthorized (token missing/invalid). Try `svcs login ...` again.", 1)
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

    for tg, head in data.get("twigs", {}).items():
        set_twig_head(tg, head)

    print(f"pulled .svcs data from {remote_name}/{username}/{remote['repo']}")

def clone(url, repo, folder, username=None, twig="main"):
    ensure_requests()
    if not username:
        die("clone requires --user <username> (per-user scope).", 2)

    if os.path.exists(folder):
        die(f"folder {folder} already exists")

    os.makedirs(folder)
    os.chdir(folder)

    init()
    remote_add("origin", url, repo)

    # pull needs auth; clone is happening inside the new repo so token must exist in this repo too
    pull("origin", username=username)

    head_commit = twig_head(twig)
    if not head_commit:
        print("clone: remote has no commits yet; cloned empty repo")
        return

    remote_cfg = _get_remote("origin")
    headers = _auth_headers(remote_cfg["url"], username)
    if not headers:
        die(f"no token found for {remote_cfg['url']} as {username}. Run: svcs login {remote_cfg['url']} {username} <password>", 1)

    r = requests.get(f"{remote_cfg['url']}/snapshot/{username}/{remote_cfg['repo']}/{head_commit}", headers=headers)
    if r.status_code != 200:
        die(f"clone failed to fetch snapshot for commit {head_commit} ({r.status_code}): {r.text}")

    snapshot = r.json()
    _write_working_tree_snapshot(snapshot)
    print(f"cloned {url} (repo={repo}) into {folder} at {twig}@{head_commit}")

# - CLI
def usage():
    print(
        "svcs <command>\n\n"
        "local commands:\n"
        "  init\n"
        "  add <file|.>\n"
        "  commit <message>\n"
        "  log\n"
        "  status\n"
        "  diff\n"
        "  twig <name>\n"
        "  checkout <twig|commit>\n"
        "  timeline\n"
        "  info\n"
        "\nremote commands:\n"
        "  remote add <name> <remote-server-url> <repo>\n"
        "  push <remote> [twig] --user <username>\n"
        "  pull <remote> --user <username>\n"
        "  clone <remote-server-url> <repo> <folder> --user <username>\n"
        "  login <remote-server-url> <username> <password>\n"
    )

def _pop_flag(args, flag):
    """
    Returns (value, remaining_args).
    Supports: --flag value
    """
    if flag not in args:
        return None, args
    i = args.index(flag)
    if i == len(args) - 1:
        die(f"missing value after {flag}", 2)
    val = args[i + 1]
    remaining = args[:i] + args[i + 2 :]
    return val, remaining

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
    elif cmd == "log":
        log()
    elif cmd == "status":
        status()
    elif cmd == "diff":
        diff()
    elif cmd == "twig":
        twig(args[0] if args else None)
    elif cmd == "checkout":
        checkout(args[0] if args else None)
    elif cmd == "timeline":
        timeline()
    elif cmd == "info":
        info()
    elif cmd == "remote":
        if len(args) < 1 or args[0] != "add" or len(args) != 4:
            die("usage: svcs remote add <name> <remote-server-url> <repo>", 2)
        remote_add(args[1], args[2], args[3])
    elif cmd == "push":
        username, args2 = _pop_flag(args, "--user")
        if len(args2) < 1:
            die("usage: svcs push <remote> [twig] --user <username>", 2)
        push(args2[0], args2[1] if len(args2) > 1 else None, username=username)
    elif cmd == "pull":
        username, args2 = _pop_flag(args, "--user")
        if len(args2) != 1:
            die("usage: svcs pull <remote> --user <username>", 2)
        pull(args2[0], username=username)
    elif cmd == "clone":
        username, args2 = _pop_flag(args, "--user")
        if len(args2) != 3:
            die("usage: svcs clone <remote-server-url> <repo> <folder> --user <username>", 2)
        clone(args2[0], args2[1], args2[2], username=username)
    elif cmd == "login":
        if len(args) != 3:
            die("usage: svcs login <remote-server-url> <username> <password>")
        login(args[0], args[1], args[2])
    else:
        die("unknown command. Run `svcs` with no args to see usage.", 2)

if __name__ == "__main__":
    main()