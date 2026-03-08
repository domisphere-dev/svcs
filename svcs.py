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
def ensure_repo():
    if not os.path.exists(SVCS_DIR):
        print("Not an SVCS repo! Did you forget to init? Smh.")
        sys.exit(1)

def sha1(data):
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
    index = read_json(INDEX)
    if target == ".":
        files = get_all_files()
    else:
        files = [target]
    for file in files:
        if not os.path.exists(file):
            continue
        with open(file, "rb") as f:
            data = f.read()
        h = sha1(data)
        obj_path = f"{OBJECTS}/{h}"
        if not os.path.exists(obj_path):
            with open(obj_path, "wb") as f:
                f.write(data)
        index[file] = h
        print(f"added {file}")
    write_json(INDEX, index)

# - COMMIT
def commit(message):
    ensure_repo()
    index = read_json(INDEX)
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
    write_json(f"{COMMITS}/{commit_id}.json", commit_data)
    set_branch_head(branch, commit_id)
    print(f"commit {commit_id} - {message} (yes, you made history)")

# - LOG
def log():
    ensure_repo()
    branch = current_branch()
    commit = branch_head(branch)
    while commit:
        data = read_json(f"{COMMITS}/{commit}.json")
        print(f"commit {commit}")
        print(f"message: {data['message']}")
        print()
        commit = data["parent"]

# - CHECKOUT
def checkout(target):
    ensure_repo()
    branch_path = f"{BRANCHES}/{target}"
    if os.path.exists(branch_path):
        with open(HEAD, "w") as f:
            f.write(target)
        commit = branch_head(target)
        restore_commit(commit)
        print(f"Switched to branch {target}")
        return
    restore_commit(target)
    print(f"Checked out commit {target}")

def restore_commit(commit):
    if not commit:
        return
    data = read_json(f"{COMMITS}/{commit}.json")
    for path, obj in data["files"].items():
        with open(f"{OBJECTS}/{obj}", "rb") as f:
            content = f.read()
        Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)

# - BRANCH
def branch(name):
    ensure_repo()
    branch = current_branch()
    commit = branch_head(branch)
    set_branch_head(name, commit)
    print(f"branch {name} created at {commit} (you fancy now)")

# - TIMELINE
def timeline():
    ensure_repo()
    branch = current_branch()
    commit = branch_head(branch)
    while commit:
        data = read_json(f"{COMMITS}/{commit}.json")
        print(f"* {commit} ({data['branch']})")
        print(f"| {data['message']}")
        print("|")
        commit = data["parent"]

# - STATUS
def status():
    ensure_repo()
    index = read_json(INDEX)
    changed = []
    staged = list(index.keys())
    all_files = get_all_files()
    for f in all_files:
        with open(f, "rb") as file:
            h = sha1(file.read())
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
    for file, h in index.items():
        obj_path = f"{OBJECTS}/{h}"
        if not os.path.exists(obj_path):
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

# - CLI
def main():
    if len(sys.argv) < 2:
        print("svcs <command>")
        return
    cmd = sys.argv[1]
    if cmd == "init":
        init()
    elif cmd == "add":
        add(sys.argv[2])
    elif cmd == "commit":
        commit(sys.argv[2])
    elif cmd == "log":
        log()
    elif cmd == "checkout":
        checkout(sys.argv[2])
    elif cmd == "branch":
        branch(sys.argv[2])
    elif cmd == "timeline":
        timeline()
    elif cmd == "status":
        status()
    elif cmd == "diff":
        diff()
    else:
        print("unknown command. Try not to break time.")

if __name__ == "__main__":
    main()