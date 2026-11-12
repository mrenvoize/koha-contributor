---
name: koha-clean-series
description: "Get a Koha branch ready for its first Bugzilla submission: one bug per branch with only its real dependencies, self-caught fix commits squashed into the commit that introduced them, specs and plans kept out, and Bug NNNNN subjects, all without interactive rebase. Use before koha-bz attaches a patchset, after a subagent-driven or multi-bug session left a messy history, or when the user says clean up the commits, squash the follow-ups, or untangle these branches."
---

Make a branch read as if it was right the first time, before anyone has seen it.

Arguments: $ARGUMENTS - optional branch or commit range (default `main..HEAD`).

Interactive rebase (`rebase -i`, `add -p`) is not available in this environment.
The techniques below are non-interactive. Never rewrite commits that are already
attached to Bugzilla without the user's say-so (see `koha-bz`).

## 1. Is this one bug, on the right base?

```bash
git log --oneline main..HEAD          # or upstream/main..HEAD in a worktree off a bare clone
```

Every commit must belong to **this** bug or to a dependency it declares. If the
range mixes bugs (common after several bugs were done in one worktree in a row,
or after committing on the wrong branch), untangle before anything else:

```bash
git branch bug_NNNNN <tip of the real dependency, or main>
git checkout bug_NNNNN
git cherry-pick <only this bug's commits, in order>
```

Branch each bug directly from the tip of the bug it genuinely depends on, not
from a sibling that merely happened to be checked out. Re-run `koha-qa` and the
relevant tests on each new branch. Before starting the next bug in the same
worktree, create its branch first, and check `git branch --show-current` before
every commit.

## 2. Squash self-caught fixes - only before the first submission

Fix-up commits (perlcritic or POD fixes, a bug found in browser testing, review
rounds from a subagent run, "(follow-up)") belong inside the commit that
introduced the problem. "(QA follow-up)" commits are a Koha convention for
changes made **after** the community QA team saw a patch, so reviewers can see
what changed. Before the first attach nobody has reviewed anything: squash.
Once a series has been attached and reviewed, do the opposite and keep genuine
follow-ups on top.

Replay onto the base, squashing each fix into its parent with `-n`:

```bash
OLD=$(git rev-parse HEAD)                     # remember the current tip
git checkout --detach <base>                  # main, or the dependency tip
git cherry-pick -n <C1> <F1> && git commit -C <C1>   # F1 squashed into C1, message and author of C1
git cherry-pick <C2> <C3>                      # untouched commits replay as they are
git diff "$OLD" HEAD                           # MUST be empty: same final tree
git branch -f bug_NNNNN HEAD && git checkout bug_NNNNN
```

If a fix conflicts when replayed onto its parent, it actually depends on a later
commit; squash it into that one instead. When the fixes touch different files
from everything else you can also use `git reset --soft <base> && git reset`,
then `git add <files>` and `git commit -C <orig>` per logical commit. Either way
the empty `git diff "$OLD" HEAD` is the proof nothing was lost; don't move the
branch pointer until it is.

## 3. Message and content hygiene

- Subjects start with `Bug NNNNN: `; the message explains why, and has a
  **librarian-facing test plan** (UI steps first, see `koha-bz`).
- Code comments added in fix rounds should be as terse as the surrounding file;
  prefer none to a rationale paragraph.
- No specs, plans or brainstorming notes in the branch (no `docs/superpowers/`,
  no AI working notes). Keep them in `core/notes/` or an untracked/planning
  branch, never committed to a branch that goes to Bugzilla.
- Dropping a doc commit from your own unpushed branch is
  `git rebase --onto <parent-of-first> <last-doc-commit> <branch>`; only do that
  when those commits are clean and unpushed, and say so before any force-push.

## 4. Prove it

```bash
git log --oneline main..HEAD       # only this bug's commits, in order
git diff --stat main..HEAD
```

Then run `koha-qa` (and the tests) on the cleaned branch, and show the user the
result before handing over to `koha-bz`.
