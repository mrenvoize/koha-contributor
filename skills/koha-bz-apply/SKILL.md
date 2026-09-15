---
name: koha-bz-apply
description: Apply a Koha bug's patches from Bugzilla — including its "Depends on" chain — to a worktree via `git bz apply`, non-interactively. Use when the user wants to test, QA, or review someone else's patch by bug number rather than working from their own branch (e.g. "apply bug 43518", "pull down this patch to test it", "check out the patches for bug NNNNN").
---

Apply a bug's patchset (and its dependency chain) with `git bz apply`.

Arguments: $ARGUMENTS — a bug number, e.g. `43518`.

## Pre-flight — the worktree `core.bare` trap

KTD's `run.sh` sets `extensions.worktreeConfig=true` on the shared bare
repo (to give worktrees a private `core.hooksPath`). Once that's set by
*any* prior KTD boot, every linked worktree inherits `core.bare=true`
from the shared bare-repo config instead of being treated as a normal
work tree — regardless of `cwd`. `git bz apply`'s internal `git am -3`
then fails with:

```
fatal: this operation must be run in a work tree
```

Before applying, check and fix it if needed:

```bash
git rev-parse --is-bare-repository   # should print "false"
```

If it prints `true`:

```bash
git config extensions.worktreeConfig true
git config --worktree core.bare false
```

This is a per-worktree fix — a freshly created worktree needs it applied
once before its first `git am`/`git bz apply`.

## Run

```bash
git bz apply --non-interactive --follow-status "Signed Off,Passed QA" NNNNN
```

- `--non-interactive` auto-confirms patch selection (equivalent to
  `--confirm`) — required, otherwise it hangs waiting for a prompt, same
  failure mode as `git bz create`/`attach` without `-y`.
- `--follow-status` is repeatable and/or comma-separated. It restricts
  which dependency bugs in the "Depends on" chain get auto-applied, by
  their Bugzilla status. Omit it to follow all dependencies regardless of
  status.
- You can pass several bug numbers in one call to apply more than one
  independently.

## Interpreting the result

- **Exit code 3** — a dependency bug isn't in an allowed `--follow-status`
  state (`DependencyNotReady`). This is not a setup problem: tell the user
  which dependency bug and what status it's actually in, then ask whether
  to widen `--follow-status` or apply that dependency manually first.
  Any other non-zero exit is a genuine error — read the message.
- **"Already applied" for a bug** — reported distinctly from a fresh
  success. Don't reinterpret it as "nothing happened" or retry; it means
  those patches are already on the branch.
- **`git am -3` conflict mid-chain** — resolve the conflict
  (`git am --continue` after fixing, or `--skip`/`--abort`), then re-run
  the same `git bz apply` command. It resumes the rest of the dependency
  chain from where it left off — no need to restart from the first bug.

## After applying

Suggest the appropriate next skill: `koha-qa` to run the QA script,
`koha-prove`/`koha-cypress` for tests, or `koha-review` for a full
patchset review — don't run them automatically.
