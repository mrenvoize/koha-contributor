---
name: koha-workflow
description: Choose and follow a Koha development workflow - either a single shared KTD instance (`kohadev`) with branches switched in one clone, or one git worktree plus one named, proxied KTD instance per bug (`bug_NNNNN`). Use when starting work on, testing, or QAing a Koha bug and no workflow preference is known yet (ask the user once), or when the user works per-bug and needs a worktree/instance set up, resumed, rebased, or cleaned up.
---

Pick a Koha workflow, then set up the environment for a bug.

Arguments: $ARGUMENTS — optional bug number, e.g. `43518`.

## Step 1 — Find out which workflow the user prefers

Two workflows are supported. The other skills default to **shared**.

| | Shared (default) | Per-bug |
|---|---|---|
| Git | One Koha clone, one branch per bug, `git switch` between them | One `git worktree` per bug, branch `bug_NNNNN`; main clone stays on `main` |
| KTD | One instance, `kohadev` | One instance per bug, `--proxy --name bug_NNNNN` |
| UI | `localhost:8081` (staff), `localhost:8080` (OPAC) | `bug_NNNNN-intra.localhost`, `bug_NNNNN.localhost` |
| Good for | Fewer resources, one bug at a time | Several bugs in flight, QAing while developing, a clean DB per bug, no rebuild/restart churn when switching |
| Cost | Switching branches means `updatedatabase`, `restart_all`, rebuilds | Each instance is a full stack (DB, memcached, search engine); needs RAM and disk |

Do **not** ask if the preference is already known. Treat any of these as an answer:

- The user stated it, or project `CLAUDE.md` / memory records it.
- The current directory is a worktree on a `bug_NNNNN` branch
  (`git rev-parse --git-dir` differs from `--git-common-dir`).
- `ktd --list` shows running `bug_*` instances.

Otherwise ask once, with the table above as context. After they answer,
offer to record the choice (e.g. a line in the project `CLAUDE.md` like
`Koha workflow: per-bug, worktrees in ~/git/koha-worktrees`) so it isn't
asked again.

If they choose **shared**, stop here. The other skills already target
`kohadev`.

## Shortcut — `kd` is installed

If `command -v kd` succeeds (the `koha-dev-scripts` wrapper), prefer it
over Steps 2–3 and the manual clean-up. It uses worktrees under
`$KOHA_DIR/core/worktrees/<name>`, applies the `core.bare` fix, boots a
proxied instance named `<name>`, and exports `KTD_INSTANCE`/`SYNC_REPO` in
its tmux dev window:

```bash
kd up bug_NNNNN [--bz]       # worktree + KTD instance; --bz applies the bug's patches
kd wt bug_NNNNN [--bz]       # worktree only
kd shell bug_NNNNN           # container shell
kd down bug_NNNNN            # stop instance and remove worktree (branch kept)
kd list                      # all worktrees, Bugzilla status, container state
```

Steps 4 and "Resuming" still apply; skip Steps 2–3 and use `kd down` for
clean-up (it keeps the branch unless `--rm=full`; confirm before using that).

## Step 2 — Per-bug: create or reuse the worktree

Ask for (or infer from the user's setup) the main clone (usually
`$SYNC_REPO`) and the worktrees directory. A sibling `koha-worktrees/`
directory is a sensible default.

```bash
KOHA_CLONE=~/git/koha            # main clone, stays on main
WT=~/git/koha-worktrees/bug_NNNNN

git -C "$KOHA_CLONE" worktree list            # reuse if it already exists
git -C "$KOHA_CLONE" fetch origin
git -C "$KOHA_CLONE" worktree add --track -b bug_NNNNN "$WT" origin/main
```

- Base on `origin/main` unless the user names another branch (e.g. a
  stable branch for a backport).
- If the worktree already exists, check its state first
  (`git -C "$WT" status`, `git -C "$WT" log --oneline origin/main..`).
  Never reset, rebase, or delete it without asking.
- Check `git -C "$WT" rev-parse --is-bare-repository` prints `false`. If
  it prints `true`, apply the `core.bare` fix described in `koha-bz-apply`
  before any `git am` / `git bz apply`.

To test or QA someone else's patches, run `koha-bz-apply` from inside
`$WT`.

## Step 3 — Per-bug: bring up the instance

Always use `--proxy` with a name. Without it, instances bind the same host
ports and collide.

```bash
ktd_proxy --status || ktd_proxy --start          # shared Traefik, once per machine
SYNC_REPO="$WT" ktd --name bug_NNNNN --proxy up -d
ktd --name bug_NNNNN --wait-ready 180
```

- **Override `SYNC_REPO` on every `up`/`down`.** If it falls back to the
  globally exported value, the stack mounts the main clone instead of the
  worktree. KTD detects worktrees and also mounts the main clone's `.git`,
  so `git`, `koha-qa.pl` and `tidy.pl` work inside the container.
- After applying patches that touch the DB or Perl:
  `ktd --name bug_NNNNN --shell --run 'updatedatabase && restart_all'`.
- Add `--single-plugin`, `--search-engine`, etc. as needed (`ktd --help`).

## Step 4 — Per-bug: point the other skills at the instance

`koha-prove`, `koha-build`, `koha-qa`, `koha-schema-apply` and
`koha-cypress` read `KTD_INSTANCE`. Shell state does **not** persist
between tool calls, so set it on each command rather than exporting it
once:

```bash
KTD_INSTANCE=bug_NNNNN ktd --name "${KTD_INSTANCE:-kohadev}" --shell --run 'prove -v t/db_dependent/Koha/Foo.t'
```

(Or pass `--name bug_NNNNN` directly.) Run git and file edits from `$WT`,
not from the main clone.

For Cypress on the host:

```bash
KOHA_INTRANET_URL=http://bug_NNNNN-intra.localhost \
KOHA_OPAC_URL=http://bug_NNNNN.localhost \
npx cypress run --spec "<path>"
```

## Resuming, rebasing, cleaning up

- **Resume:** `ktd --list`. If the instance is down,
  `SYNC_REPO="$WT" ktd --name bug_NNNNN --proxy up -d` again.
- **Rebase onto fresh main** (ask first if there are local commits):
  `git -C "$WT" fetch origin && git -C "$WT" rebase origin/main`, then
  `updatedatabase && restart_all` in the instance.
- **Clean up** (only when the user asks, and only instances they started):
  ```bash
  SYNC_REPO="$WT" ktd --name bug_NNNNN down
  git -C "$KOHA_CLONE" worktree remove "$WT"
  git -C "$KOHA_CLONE" branch -D bug_NNNNN
  ```
  Unpushed commits are lost when the branch is deleted. Check
  `git -C "$WT" log --oneline origin/main..` and confirm first.

## Output

Report the workflow in use, the worktree path and branch, the instance
name and its staff/OPAC URLs, and the `KTD_INSTANCE=...` prefix to use for
the rest of the session.
