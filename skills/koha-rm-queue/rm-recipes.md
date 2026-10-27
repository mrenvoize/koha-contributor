# RM recipes (companion to koha-rm-queue)

Conditional recipes run **only on the maintainer's instruction**. All of
`koha-rm-queue`'s non-negotiables apply here: never sign, never touch
Bugzilla without approval, never force-push, never hard-code names, emails,
instance names or home paths.

## The DBRev commit ("add the DBRev")

One commit per DB-changing bug, authored by the RM, subject
`Bug NNNNN: DBRev <version>`. Derive the next version — **never invent it**:

```bash
grep -n 'VERSION = ' Koha.pm | head -2          # current $VERSION, e.g. "26.06.00.042"
ls installer/data/mysql/db_revs | tail -3       # last rev file, e.g. 260600042.pl
git log upstream/main --grep='DBRev' --format='%h %s' -3   # how earlier RM commits did it
```

The next version increments the last component; the `db_revs` filename is
the version with the dots removed (`26.06.00.043` -> `260600043.pl`). Then:

```bash
git mv installer/data/mysql/atomicupdate/bug_NNNNN.pl installer/data/mysql/db_revs/<digits>.pl
# edit Koha.pm: $VERSION = "<version>";
git add Koha.pm
git commit -m "Bug NNNNN: DBRev <version>"
```

with the maintainer's trailer if sign-offs are on for this run. Verify in
KTD:

```bash
ktd --name "$INSTANCE" --shell --run 'perl installer/data/mysql/updatedatabase.pl'
```

and confirm it upgrades cleanly to the new version and
`installer/data/mysql/atomicupdate/` is empty again.

## Restore sign-offs ("restore sign-offs")

When a previous step dropped someone's `Signed-off-by` lines: recover them
from the bug's patch attachments on Bugzilla — the attachment bodies carry
the original trailers (fetch via `git bz` / the `GitBz` client, reading
only). Re-add them with `git commit --amend --no-edit --trailer
"Signed-off-by: <as found>"` per affected commit, in the original order,
preserving every existing trailer. Show the before/after trailer list to the
maintainer.

## Reorder and squash by replay ("reorder"; Gate 1 noise squash)

Never use interactive `rebase -i`, and never reorder or squash on your own.
With the maintainer's approval:

1. **Back up**: `git branch -f backup/pre_replay_<date> HEAD`.
2. **Replay**: `git reset --hard <base>` (the commit below the range), then
   `git cherry-pick <sha>...` in the new order — or, for a squash of your
   own noise commits, cherry-pick the logical commit and apply each fixup
   with `git cherry-pick -n <fixup>` + `git commit --amend --no-edit`.
3. **Verify the final tree is identical**:
   `git diff backup/pre_replay_<date> HEAD` must be empty. If it is not,
   stop, show the diff, and offer to restore the backup
   (`git reset --hard backup/pre_replay_<date>`).
4. On conflicts during the replay: resolve only trivial, mechanical ones
   (e.g. a test-plan count both sides touched) and say what you did;
   anything substantive, stop and ask.
5. **Bugzilla patches are never squashed, reworded or dropped** — a reorder
   changes only their order; a squash touches only your own fixup/noise
   commits. RM follow-ups and DBRevs stay separate commits.

After a reorder, offer the matching Bugzilla `depends_on` updates (the exact
add/remove per bug) for approval, then post them via the Gate 3 client
(`update_bug($id, depends_on => { add => [...], remove => [...] })`).
Keep the backup branch until the batch is pushed and verified; offer to
delete it at the end.
