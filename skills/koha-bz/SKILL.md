---
name: koha-bz
description: File a Koha bug on bugs.koha-community.org and attach commits non-interactively via git bz. Use when the user wants to submit a patch, file a bug, or open a bz/Bugzilla ticket for Koha. Arguments (optional, free-form): summary or component hints. Without args, derive details from the current branch and HEAD commits.
---

File a Koha Bugzilla bug and attach commits using `git bz` non-interactively.

Arguments: $ARGUMENTS

## CRITICAL: Never invoke proactively

**This skill must only run when the user explicitly asks to file a bug or attach
patches** (e.g. "file the bug", "attach the patches", "run git bz", "submit to
Bugzilla"). Never invoke it automatically after completing code changes — even
if the commits look ready. Always wait for an explicit instruction from the
user before taking any Bugzilla action.

## Why this skill exists

`git bz create` and `git bz attach` default to interactive prompts and will hang
when run from Claude Code. Both commands need `-y` plus all required fields
passed as flags. This skill encodes the full workflow so the model doesn't
re-derive it (and doesn't omit `-y`, which is the most common failure mode).

## Pre-flight

1. Confirm `git bz` is installed: `command -v git-bz || git bz --help`. If
   missing, stop and tell the user to install `git-bz` and run
   `git bz --help` once to populate `~/.git-bz` with their Bugzilla creds.
2. Confirm the current branch has commits ahead of `main` (Koha community
   uses `main`, not `master`):
   `git log --oneline main..HEAD`. If empty, stop — there's nothing to attach.
3. Read the first commit's subject line; Koha convention is
   `Bug NNNNN: <summary>`. If the user already has a bug number in their
   commits, skip creation and go straight to attach.

## Step 1 — Gather bug fields

Required for `git bz create`:

| Flag         | Notes                                                |
|--------------|------------------------------------------------------|
| `--product`  | Almost always `Koha`                                 |
| `--comp`     | e.g. `Circulation`, `Cataloging`, `Acquisitions`, `Hold requests`, `OPAC`, `Staff interface`, `REST API`, `Templates`, `Test Suite`. Ask the user if not obvious. |
| `--version`  | `main` for unreleased work                           |
| `--severity` | `normal` unless user says otherwise (`enhancement` for new features, `minor`, `major`, `critical`) |
| `--summary`  | < 80 chars; do NOT prefix with `Bug NNNNN:`          |
| `--desc`     | Multi-line body; pass via heredoc                    |

If the user didn't supply the summary/component, propose values derived from
the branch name and HEAD commit subject, then confirm with the user before
running. Do not invent a component — ask if uncertain.

Description body should follow the Koha template:

```
This patch <does X>.

Test plan:
1. <step>
2. <step>
3. <expected result>

Sponsored-by: <if applicable>
```

### Text formatting — plain text, no markdown

Bugzilla renders the summary and description as **plain text**, not markdown.
Get the encoding right or comments come out mangled:

- **No markdown.** Don't use `**bold**`, `` `code` ``, `#` headings, `[]()`
  links, or `-`/`*` bullet syntax for emphasis — they render literally as the
  raw characters. Plain numbered/dashed lists in the test plan are fine because
  they read naturally as text, not because Bugzilla formats them.
- **ASCII punctuation only.** Use straight quotes (`'` `"`), `-` for hyphens
  and `--` for dashes, and `...` for ellipses. Do NOT use "smart" typographic
  characters — curly quotes (`'` `'` `"` `"`), en/em dashes (`–` `—`), or the
  ellipsis glyph (`…`). These are the "oddly encoded characters in the middle
  of words" that show up when an editor or model auto-substitutes them.
- **UTF-8 is allowed where it carries meaning** — e.g. an author's name with
  accents (`José`, `Müller`) or a genuine non-Latin string. Keep it as real
  UTF-8; never paste mojibake (`Ã©`, `â€"`) — if you see that, the text was
  double-encoded and must be fixed before submitting.
- Before running create/attach, **scan the summary and `--desc` body for any
  non-ASCII byte** and confirm each one is intentional UTF-8, not a stray smart
  quote or mojibake.

## Step 2 — Dry run first

Always run with `--dry-run` first to surface duplicates and missing-field
errors without creating a bug:

```bash
git bz create --dry-run \
  --product "Koha" \
  --comp "<Component>" \
  --version "main" \
  --severity "normal" \
  --summary "<short summary>" \
  --desc "$(cat <<'EOF'
<body>
EOF
)"
```

Show the dry-run output to the user. If duplicates are flagged, stop and let
the user decide whether to proceed or attach to the existing bug instead.

## Step 3 — Create the bug

After user confirmation, repeat the command without `--dry-run` and with `-y`
to skip the final confirmation prompt:

```bash
git bz create -y \
  --product "Koha" \
  --comp "<Component>" \
  --version "main" \
  --severity "normal" \
  --summary "<short summary>" \
  --desc "$(cat <<'EOF'
<body>
EOF
)"
```

Capture the bug number from the output line:
`Bug NNNNN created: https://bugs.koha-community.org/...`.

## Step 4 — Rewrite commit subjects (if needed)

Koha requires every commit subject to start with `Bug NNNNN: `. If commits
were authored before the bug existed, offer to rebase and prepend. Do NOT
rewrite published commits without user confirmation.

## Step 5 — Attach commits

Pass `-y` to skip per-commit confirmation prompts. Use a commit range that
covers everything from the branch point:

```bash
git bz attach -y NNNNN main..HEAD
```

Or for a fixed count: `git bz attach -y NNNNN HEAD~3..HEAD`.

## Attaching updates obsoletes prior attachments by default

Since `git-bz` 1.2.0, `git bz attach` marks the patches it supersedes as
obsolete **and tags the corresponding bug comments** — this is the default,
not opt-in. Re-attaching a revised series will silently obsolete the
previous one; that's usually what you want, but say so explicitly to the
user before attaching a revision so it isn't a surprise.

- `git bz attach --no-comment HEAD` — attach without adding a comment at all.
- `git bz attach --no-obsolete-comments HEAD` — still obsoletes superseded
  attachments, but skips tagging the bug comments about it.

## Claiming QA contact / changing status non-interactively

`git bz edit --non-interactive` (added in 1.3.0) updates a bug without
opening an editor — useful for claiming QA contact before testing a patch:

```bash
git bz edit --non-interactive --qa-contact "$(git config user.email)" NNNNN
```

It requires at least one field option: `--status`, `--comment`,
`--patch-complexity`, `--sponsorship`, `--sponsor`, `--depends`,
`--assignee`, `--qa-contact`, or `--obsolete`.

## Common failure modes

- **Process hangs / no output** — missing `-y`. Kill it and retry with `-y`.
- **`Missing required field`** — one of `--product/--comp/--version/--summary/--desc` was omitted. Re-run with all five.
- **`No such component`** — component name is case-sensitive and must match Bugzilla exactly. Run a dry-run with a guess and read the error to find valid values, or ask the user.
- **Auth failure** — usually `~/.git-bz` is missing or stale; tell the user
  to run `git bz --help` interactively to refresh credentials. But if
  credentials look fine and requests still fail, check the tracker config
  itself is set — `git bz` needs `bz-tracker.<host>.path` and `.https`
  configured (e.g. `git config bz-tracker.bugs.koha-community.org.path
  /bugzilla3` and `git config bz-tracker.bugs.koha-community.org.https
  true`), not just credentials. Do not attempt to write auth files from the
  skill.
- **Branch is `master`, not `main`** — Koha community uses `main`. The local default may say `master` but it's stale. Use `main..HEAD` for the attach range.
- **`main..HEAD` fails with exit 128 / "unknown revision"** — common in a
  `git worktree` off a shared bare clone when the upstream remote isn't
  literally named `origin`/`main`. Check `git remote -v` and fall back to
  `upstream/main..HEAD` (or whatever the actual remote is called) rather
  than assuming `main` resolves.
- **Rewriting history on a branch that's already been attached** — once
  commits are attached to Bugzilla, don't rebase/force-push over them
  without a reason. Old attachments reference specific SHAs; if those
  commits get garbage-collected after a rebase, you're left manually
  reconstructing a "needs rebase" patch series later. Prefer new commits
  (or a clearly-superseding rebase you immediately re-attach) over silently
  losing the old SHAs.

## Output to user

Report:
- Bug URL (from the create output)
- Number of commits attached
- The exact `git bz attach` command used, in case they need to re-run it
