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

## Common failure modes

- **Process hangs / no output** — missing `-y`. Kill it and retry with `-y`.
- **`Missing required field`** — one of `--product/--comp/--version/--summary/--desc` was omitted. Re-run with all five.
- **`No such component`** — component name is case-sensitive and must match Bugzilla exactly. Run a dry-run with a guess and read the error to find valid values, or ask the user.
- **Auth failure** — `~/.git-bz` is missing or stale. Tell the user to run `git bz --help` interactively to refresh credentials; do not attempt to write that file from the skill.
- **Branch is `master`, not `main`** — Koha community uses `main`. The local default may say `master` but it's stale. Use `main..HEAD` for the attach range.

## Output to user

Report:
- Bug URL (from the create output)
- Number of commits attached
- The exact `git bz attach` command used, in case they need to re-run it
