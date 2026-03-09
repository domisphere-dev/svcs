# SVCS - The Simple Version Control System

this is a **really dumb** project i made out of pure boredom. like *literally*.

i wanted a tiny version control thing that kinda smells like git, but also definitely isn’t git (because i value my sanity and also i wrote this in python).

## What is this?

**svcs** = “simple version control system” (or “severely questionable coding session”, both are accurate).

you get a little cli (`svcs.py`) that tracks file history locally inside a `.svcs/` folder.

- is it production ready? **no.**
- is it educational? **yeah, i guess.**
- will it eat your files? **probably not.** (but i’m not making promises)

> tl;dr: it’s a learning/toy vcs. if you use this for real work… that’s on you.

---

## Requirements

- python **3.9+**
- an adventurous spirit

no external deps. just vibes.

---

## Installation

clone it and run it:

```bash
git clone <your-repo-url>
cd svcs
python3 svcs.py
```

---

## Commands (aka “the buttons i managed to wire up”)

### `init`
make a new svcs repo in the current folder.

```bash
python3 svcs.py init
```

creates:

- `.svcs/objects/` — stored file contents (sha-1 addressed, because i’m fancy)
- `.svcs/commits/` — commit json files
- `.svcs/branches/` — branch pointers
- `.svcs/index.json` — staging index
- `.svcs/HEAD` — current branch name

---

### `add <file|.`
stage one file or everything.

```bash
python3 svcs.py add main.py
python3 svcs.py add .
```

`add .` walks folders recursively and respects `.svcsignore`.

---

### `commit <message>`
commit what’s staged.

```bash
python3 svcs.py commit "initial commit"
```

commits store:

- message
- timestamp
- mapping of tracked paths → content hashes
- parent commit id
- branch name

---

### `log`
show commit history.

```bash
python3 svcs.py log
```

---

### `status`
show staged + modified/unstaged files.

```bash
python3 svcs.py status
```

---

### `diff`
show line-level diffs between staged and working dir.

```bash
python3 svcs.py diff
```

---

### `branch <name>`
create a branch pointer.

```bash
python3 svcs.py branch feature-x
```

---

### `checkout <branch|commit>`
switch branches or restore a commit.

```bash
python3 svcs.py checkout feature-x
python3 svcs.py checkout a1b2c3d
```

---

### `timeline`
print a tiny ascii commit timeline.

```bash
python3 svcs.py timeline
```

---

### `info`
print version/info.

```bash
python3 svcs.py info
```

---

## Ignoring files: `.svcsignore`

make a `.svcsignore` file in the repo root to stop stuff from being tracked.

example:

```gitignore
*.log
*.tmp
dist/
build/
node_modules/
.venv/
```

`.svcs/` is always ignored automatically (because i’m not a monster).

---

## Typical Workflow (how i expected this to be used at 2am)

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

## Remote stuff (yes, somehow)

ok so… turns out there’s "remote" features in here. not *git* remotes. more like "i duct-taped HTTP onto my toy vcs" remotes.

### a few important things before you get excited:

- this repo is **only the client** (`svcs.py`). you need a **compatible server** that speaks SVCS over HTTP.
- the client expects these endpoints to exist on the server:
  - `POST /create/<repo>`
  - `POST /push/<repo>`
  - `GET  /pull/<repo>`
  - `GET  /snapshot/<repo>/<commit>`

### the one dependency i couldn’t avoid

remote stuff uses `requests`. if you don’t have it, svcs will yell at you (fair).

```bash
pip install requests
```

### `remote add <name> <url> <repo>`

adds a remote to `.svcs/remotes.json`.

```bash
python3 svcs.py remote add origin http://localhost:8000 my-repo
```

### `push <remote> [branch]`

pushes commits + objects **and** (this is the chaotic part) a full **working tree snapshot** of your current files.

- default branch is whatever you’re on
- if the server returns `404`, svcs will try to auto-create the repo by calling `POST /create/<repo>` and then push again

```bash
python3 svcs.py push origin
python3 svcs.py push origin main
```

### `pull <remote>`

pulls **only the `.svcs` database** (objects/commits/branch heads). it does **not** rewrite your working directory.

aka: it updates your "history" but doesn’t touch your "mess".

```bash
python3 svcs.py pull origin
```

### `clone <url> <repo> <folder>`

makes a new folder, initializes svcs inside it, sets `origin`, pulls the `.svcs` data, then fetches a snapshot for the current head commit and writes it into the working tree.

```bash
python3 svcs.py clone http://localhost:5000 my-repo ./my-repo
```

---


## Notes / Limitations (aka “things i didn’t implement”)

- no merge, no rebase, no conflict resolution.
- commit ids are short sha-1-derived identifiers (collisions *should* be rare… probably).
- this is meant for learning and small experiments.

---

## License

This project is MIT Licensed. Do whatever you want with it, just don’t sue me if your files get lost in the time vortex.
