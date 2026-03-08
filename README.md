# SVCS - Simple Version Control System

**SVCS** is a minimal, hobbyist version control system written in Python.
It’s designed as a **proof-of-concept** to explore the inner workings of version control, without all the complexity of Git.
Think of it as Git, but *tiny*, *fun*, and *educational*.

> ⚠️ This is **not meant for production use**. Use it on personal projects or for learning purposes only.

---

## Features

SVCS supports the core workflow that most developers use daily:

* `init` - initialize a new repository (`.svcs/` folder)
* `add <file>` - stage a single file
* `add .` - stage all files recursively (respects `.svcsignore`)
* `.svcsignore` - ignore files/folders (like `.gitignore`)
* `commit <message>` - commit staged files with a message
* `log` - show commit history for the current branch
* `branch <name>` - create a new branch
* `checkout <branch|commit>` - switch to a branch or restore a commit
* `timeline` - ASCII timeline of commits
* `status` - show staged and modified/unstaged files
* `diff` - show differences between staged files and working directory

---

## How It Works

SVCS is intentionally **simple and educational**, built entirely in Python.

* Files are stored in `.svcs/objects` using **SHA-1 hashes** for content tracking
* Commits are JSON files in `.svcs/commits` storing:

  * Commit message
  * Timestamp
  * File hashes
  * Parent commit

* Branches are **pointers to commits** stored in `.svcs/branches`
* The current branch is stored in `.svcs/HEAD`
* `.svcsignore` allows you to skip files/folders from being tracked

It’s basically a tiny, hand-coded Git clone with just the commands you actually need.
Great for **learning how version control works under the hood**.

---

## Installation

1. Make sure you have **Python 3.9+** installed
2. Clone the repository:

```
git clone <your-repo-url>
cd svcs
```

3. You can run it directly:

```
python svcs.py init
python svcs.py add .
python svcs.py commit "first commit"
```

No dependencies required. Just Python.

> Tip: You can make it globally executable with a simple wrapper or `chmod +x svcs.py`.

---

## Usage Examples

```
# Initialize repo
python svcs.py init

# Add files
python svcs.py add main.py
python svcs.py add .

# Commit changes
python svcs.py commit "initial commit"

# Create a new branch
python svcs.py branch feature-ui

# Switch branch
python svcs.py checkout feature-ui

# Show current status
python svcs.py status

# See differences
python svcs.py diff

# View commit history
python svcs.py log

# View timeline
python svcs.py timeline

# Checkout a previous commit
python svcs.py checkout a03829
```

---

## .svcsignore

You can create a `.svcsignore` file in your project root to ignore files/folders. Example:

```
*.log
*.tmp
build/
dist/
node_modules/
.svcs/
```

`.svcs/` is automatically ignored to prevent tracking internal data.

---

## Philosophy

SVCS is:

* Small and simple (~300 lines of Python)
* Designed for **fun, learning, and tinkering**
* Not intended to replace Git or be used for critical projects
* A stepping stone if you want to build **your own personal version control platform**

Think of it as a **mini time machine for your files**.

---

## Contributing

Contributions are welcome! Suggestions for:

* Improved `diff` output
* CLI enhancements
* Better timeline visualization
* Educational comments or explanations

…are all encouraged. Keep it fun and minimal.

---

## License

This project is **MIT Licensed**.
Do whatever you want with it, just don’t sue me if your files get lost in the time vortex.

---

## Fun Fact

SVCS was made as a hobby project by a developer who wanted to:

* Understand version control better
* Play with Python file storage
* Make something funny and educational at the same time

So don’t expect fancy merge tools… yet.

---