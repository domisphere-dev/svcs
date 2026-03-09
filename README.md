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

## Notes / Limitations (aka “things i didn’t implement”)

- no merge, no rebase, no conflict resolution.
- commit ids are short sha-1-derived identifiers (collisions *should* be rare… probably).
- this is meant for learning and small experiments.

---

## License

This project is MIT Licensed. Do whatever you want with it, just don’t sue me if your files get lost in the time vortex.
