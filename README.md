# SVCS (Client) — Simple Version Control System

SVCS is a small, educational version control tool written in Python.  
This repository focuses on the **client CLI** (`svcs.py`) that tracks file history locally in a `.svcs/` folder.

> SVCS is a learning project, not a production-ready VCS.

---

## Requirements

- Python **3.9+**

No external dependencies are required for local-only usage.

---

## Installation

Clone the repository and run the CLI directly:

```bash
git clone <your-repo-url>
cd svcs
python3 svcs.py
```

---

## Commands

### `init`
Initialize a new SVCS repository in the current folder.

```bash
python3 svcs.py init
```

Creates:

- `.svcs/objects/` — stored file contents, addressed by SHA-1
- `.svcs/commits/` — commit JSON files
- `.svcs/branches/` — branch pointers (files named by branch)
- `.svcs/index.json` — staging index
- `.svcs/HEAD` — current branch name

---

### `add <file|.>`
Stage a file (or all files) for the next commit.

```bash
python3 svcs.py add main.py
python3 svcs.py add .
```

`add .` walks the directory tree recursively and respects `.svcsignore`.

---

### `commit <message>`
Create a commit from the staged index.

```bash
python3 svcs.py commit "initial commit"
```

Commits store:
- message
- timestamp
- mapping of tracked paths → content hashes
- parent commit id
- branch name

---

### `log`
Show commit history of the current branch.

```bash
python3 svcs.py log
```

---

### `status`
Show staged files and modified/unstaged files.

```bash
python3 svcs.py status
```

---

### `diff`
Show line-level differences between staged content and the working directory.

```bash
python3 svcs.py diff
```

---

### `branch <name>`
Create a new branch pointer at the current commit.

```bash
python3 svcs.py branch feature-x
```

---

### `checkout <branch|commit>`
Switch to a branch or restore a specific commit.

```bash
python3 svcs.py checkout feature-x
python3 svcs.py checkout a1b2c3d
```

---

### `timeline`
Print a simple ASCII commit timeline.

```bash
python3 svcs.py timeline
```

---

### `info`
Print SVCS version/info.

```bash
python3 svcs.py info
```

---

## Ignoring files: `.svcsignore`

Create a `.svcsignore` file in your repo root to prevent files/folders from being tracked.

Example:

```gitignore
*.log
*.tmp
dist/
build/
node_modules/
.venv/
```

`.svcs/` is always ignored automatically.

---

## Typical workflow

```bash
python3 svcs.py init
python3 svcs.py add .
python3 svcs.py commit "first commit"

# edit files...

python3 svcs.py status
python3 svcs.py add .
python3 svcs.py commit "update"
python3 svcs.py log
```

---

## Notes / Limitations

- SVCS is intentionally minimal (no merge, no rebase, no conflict resolution).
- Commit IDs are short SHA-1-derived identifiers and are not guaranteed collision-free in large repos.
- This tool is meant for learning and small experiments.

---

## License

This project is MIT Licensed. Do whatever you want with it, just don’t sue me if your files get lost in the time vortex.