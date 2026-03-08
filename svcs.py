import os
import sys
import json
import hashlib
import time
import fnmatch
from pathlib import Path

# - Paths / Config
SVCS_DIR = ".svcs"
OBJECTS = f"{SVCS_DIR}/objects"
COMMITS = f"{SVCS_DIR}/commits"
BRANCHES = f"{SVCS_DIR}/branches"
INDEX = f"{SVCS_DIR}/index.json"
HEAD = f"{SVCS_DIR}/HEAD"
IGNORE_FILE = ".svcsignore"

# - Utils
def die(msg, code=1):
    print(msg)
    sys.exit(code)

def ensure_repo():
    if not os.path.exists(SVCS_DIR):
        die("Not an SVCS repo! Did you forget to run `svcs init`?", 1)

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

# - Ignore system
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

# - INIT
def init():
    os.makedirs(OBJECTS, exist_ok=True)
    os.makedirs(COMMITS, exist_ok=True)
    os.makedirs(BRANCHES, exist_ok=True)
    write_json(INDEX, {})
    with open(HEAD, "w") as f:
        f.write("main")
    set_branch_head("main", "")
    print("SVCS repo initialized! Time to make history, literally.")

# - ADD
def add(target):
    ensure_repo()
    if not target:
        die("usage: svcs add <file|.>", 2)

    index = read_json(INDEX)
    if target == ".":
        files = get_all_files()
    else:
        files = [target]

    added_any = False
    for file in files:
        if not os.path.exists(file):
            # keep behavior: silently skip, but it's nicer to tell the user
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

# - COMMIT
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
    print(f"commit {commit_id} - {message} (yes, you made history)")

# - LOG
def log():
    ensure_repo()
    branch = current_branch()
    commit_id = branch_head(branch)
    if not commit_id:
        print("(no commits yet)")
        return

    while commit_id:
        data = read_json(commit_path(commit_id))
        # If commit file is missing/corrupt, stop gracefully
        if not data or "message" not in data:
            print(f"(commit data missing for {commit_id})")
            return
        print(f"commit {commit_id}")
        print(f"message: {data['message']}")
        print()
        commit_id = data.get("parent")

# - CHECKOUT
def checkout(target):
    ensure_repo()
    if not target:
        die("usage: svcs checkout <branch|commit>", 2)

    branch_path = f"{BRANCHES}/{target}"
    if os.path.exists(branch_path):
        with open(HEAD, "w") as f:
            f.write(target)
        commit_id = branch_head(target)
        if commit_id:
            restore_commit(commit_id)
        print(f"Switched to branch {target}")
        return

    # commit checkout
    if not commit_exists(target):
        die(f"unknown branch or commit: {target}", 1)

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

# - BRANCH
def branch(name):
    ensure_repo()
    if not name:
        die("usage: svcs branch <name>", 2)

    cur = current_branch()
    commit_id = branch_head(cur) or ""
    set_branch_head(name, commit_id)
    print(f"branch {name} created at {commit_id} (you fancy now)")

# - TIMELINE
def timeline():
    ensure_repo()
    branch_name = current_branch()
    commit_id = branch_head(branch_name)
    if not commit_id:
        print("(no commits yet)")
        return

    while commit_id:
        data = read_json(commit_path(commit_id))
        if not data or "message" not in data:
            print(f"(commit data missing for {commit_id})")
            return
        print(f"* {commit_id} ({data.get('branch', '?')})")
        print(f"| {data['message']}")
        print("|")
        commit_id = data.get("parent")

# - STATUS
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

# - DIFF
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

def info():
    print(
        "===================================\n"
        "Simple Version System - SVCS\n"
        "Copyright (C) 2026 Dominik Hupfauer\n"
        "Version 1.0.0.0\n"
        "=====================================\n"
    )

# - CLI
def usage():
    print(
        "svcs <command>\n\n"
        "commands:\n"
        "  init\n"
        "  add <file|.>\n"
        "  commit <message>\n"
        "  log\n"
        "  status\n"
        "  diff\n"
        "  branch <name>\n"
        "  checkout <branch|commit>\n"
        "  timeline\n"
        "  info\n"
    )

def main():
    if len(sys.argv) < 2:
        usage()
        return

    cmd = sys.argv[1]

    if cmd == "init":
        init()
    elif cmd == "add":
        add(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "commit":
        commit(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "log":
        log()
    elif cmd == "checkout":
        checkout(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "branch":
        branch(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "timeline":
        timeline()
    elif cmd == "status":
        status()
    elif cmd == "diff":
        diff()
    elif cmd == "info":
        info()
    else:
        die("unknown command. Try not to break time.\n(run `svcs` with no args to see usage)", 2)

if __name__ == "__main__":
    main()