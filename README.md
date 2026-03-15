# SVCS - The Simple Version Control System

this is a **really dumb** project i made out of pure boredom. like *literally*.

i wanted a tiny version control thing that kinda smells like git, but also definitely isn't git (because i value my sanity and also i wrote this in python).

## What is this?

**svcs** = "simple version control system" (or "severely questionable coding session", both are accurate).

you get a little cli (`svcs.py`) that tracks file history locally inside a `.svcs/` folder.

- is it production ready? **no.**
- is it educational? **yeah, i guess.**
- will it eat your files? **probably not.** (but i'm not making promises)

> tl;dr: it's a learning/toy vcs. if you use this for real work... that's on you.

---

## Why "twig" and not "branch"?

because calling it a "branch" would imply i'm implementing something *remotely* close to real git.

this project is a tiny, sleep-deprived version control toy. so instead of pretending these are serious, battle-tested branches, i call them **twigs**:

- smaller
- cuter
- easier to snap in half
- and generally a more accurate representation of what's going on in here

also, if you ever find yourself arguing about twig naming conventions... please take a break, drink water, and reconsider your life choices.

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

## Commands (aka "the buttons i managed to wire up")

### `init`
make a new svcs repo in the current folder.

```bash
python3 svcs.py init
```

creates:

- `.svcs/objects/` - stored file contents (sha-1 addressed, because i'm fancy)
- `.svcs/commits/` - commit json files
- `.svcs/twigs/` - twig pointers
- `.svcs/index.json` - staging index
- `.svcs/HEAD` - current twig name

---

### `add <file|.>`
stage one file or everything.

```bash
python3 svcs.py add main.py
python3 svcs.py add .
```

`add .` walks folders recursively and respects `.svcsignore`.

---

### `commit <message>`
commit what's staged.

```bash
python3 svcs.py commit "initial commit"
```

commits store:

- message
- timestamp
- mapping of tracked paths → content hashes
- parent commit id
- twig name

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

### `twig <name>`
create a twig pointer.

```bash
python3 svcs.py twig feature-x
```

---

### `checkout <twig|commit>`
switch twigs or restore a commit.

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

`.svcs/` is always ignored automatically (because i'm not a monster).

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

## Remote stuff (yes, somehow) - now with login™

ok so... turns out there's "remote" features in here. not *git* remotes. more like "i duct-taped HTTP onto my toy vcs" remotes.

### before you continue:
- this repo is **only the client** (`svcs.py`). you need a **compatible server** that speaks SVCS over HTTP.
- the server is now **per-user scoped**:
  - your repos live on the server under: `repos/<username>/<repo>/`
  - you don’t push to some global bucket anymore. you push to *your* bucket. congratulations, you have a namespace.

### the one dependency i couldn't avoid (still)
remote stuff uses `requests`. if you don't have it, svcs will yell at you (fair).

```bash
pip install requests
```

---

## Auth (aka "login once, push forever-ish")

you now have to **login** before you can push/pull/clone.

### `login <remote-server-url> <username> <password>`

logs you in and stores a token **inside your local repo** at:

- `.svcs/remotes-token.json`

example:

```bash
python3 svcs.py login http://127.0.0.1:5000 alice secret
```

notes:
- tokens are stored *per server url + username*
- if you delete `.svcs/remotes-token.json`, that's basically logging out (very advanced security technique)

---

## `remote add <name> <remote-server-url> <repo>`

adds a remote to `.svcs/remotes.json`.

```bash
python3 svcs.py remote add origin http://127.0.0.1:5000 my-repo
```

---

## `push <remote> [twig] --user <username>`

pushes commits + objects **and** a full **working tree snapshot** of your current files.

because why send a clean diff when you can send *everything*.

```bash
python3 svcs.py push origin --user alice
python3 svcs.py push origin main --user alice
```

what it does:
- sends `.svcs` objects + commits + twigs
- also sends a working tree snapshot so the server can serve it later for clone

if you get:
- `401 unauthorized`: you forgot to login or your token is invalid
- `403 forbidden`: you're logged in as one user but trying to push as another
- `404 repo not found`: svcs will auto-create it (if possible) and push again

---

## `pull <remote> --user <username>`

pulls **only the `.svcs` database** (objects/commits/twig heads).
it does **not** rewrite your working directory.

aka: it updates your "history" but doesn't touch your "mess".

```bash
python3 svcs.py pull origin --user alice
```

---

## `clone <remote-server-url> <repo> <folder> --user <username>`

makes a new folder, initializes svcs inside it, sets `origin`, pulls the `.svcs` data,
then fetches a snapshot for the current head commit and writes it into the working tree.

```bash
python3 svcs.py clone http://127.0.0.1:5000 my-repo ./my-repo --user alice
```

---

## What endpoints does the client expect now?

your server should provide:

- `POST /login`
- `POST /create/<user>/<repo>`
- `POST /push/<user>/<repo>`
- `GET  /pull/<user>/<repo>`
- `GET  /snapshot/<user>/<repo>/<commit>`

(yes, it’s a lot of slashes. yes, it’s still HTTP. no, we are not proud.)


## Notes / Limitations (aka "things i didn't implement")

- no merge, no rebase, no conflict resolution.
- commit ids are short sha-1-derived identifiers (collisions *should* be rare... probably).
- this is meant for learning and small experiments.

---

## License

This project is MIT Licensed. Do whatever you want with it, just don't sue me if your files get lost in the time vortex.