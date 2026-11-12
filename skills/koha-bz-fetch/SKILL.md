---
name: koha-bz-fetch
description: "Fetch a Koha Bugzilla bug's summary, description, status, and recent comments from bugs.koha-community.org by bug number. Use before starting work on a bug to surface the test plan and any prior discussion. Argument: a Koha bug number (e.g. 33501)."
---

Fetch a Koha Bugzilla bug by number.

Arguments: $ARGUMENTS — a single bug number (e.g. `33501`).

## Pre-flight

Validate the argument is a positive integer. If the user passed a URL like
`https://bugs.koha-community.org/bugzilla3/show_bug.cgi?id=NNNNN`, extract
the number from the `id` parameter.

## Method 1 — git bz show (preferred if available)

If `git bz` is configured (`~/.git-bz` exists) and is perl-git-bz 1.4.0 or
newer (`git bz show --help` works), use it:

```bash
git bz show NNNNN              # details, description, all comments, attachments
git bz show --last 3 NNNNN     # description plus only the last 3 comments
git bz show --no-comments NNNNN
git bz show --json NNNNN       # bug, comments and attachments as JSON
```

It uses the user's authenticated session, so restricted (security) bugs the
user can see are readable too. Prefer `--last N` for long threads.

On an older build with no `show` subcommand, `EDITOR=cat GIT_EDITOR=cat git
bz edit NNNNN` prints the bug's metadata and exits with "No changes made"
(posts nothing). For the comment thread of a restricted bug, reuse perl-git-bz's
already-authenticated client from inside a git repo (it reads the tracker
credentials from git config), instead of hand-rolling a login:

```perl
use lib '<perl-git-bz checkout>/lib';
use GitBz::Commands;
my $comments = GitBz::Commands->new->{client}->get_comments($bug_id);
```

If you must hand-roll `rest/login`, URL-encode the login and password first
(a stored password can contain `&`, which silently truncates it and returns a
plain 401 that looks like wrong credentials). Never print the credentials.

## Method 2 — Bugzilla REST API (fallback, no auth needed for public bugs)

```bash
curl -sf "https://bugs.koha-community.org/bugzilla3/rest/bug/NNNNN" \
  | jq '.bugs[0] | {id, summary, status, resolution, severity, component, version, assigned_to, creator, creation_time, last_change_time}'
```

For comments:
```bash
curl -sf "https://bugs.koha-community.org/bugzilla3/rest/bug/NNNNN/comment" \
  | jq '.bugs["NNNNN"].comments[] | {id: .count, who: .creator, when: .creation_time, text: .text}'
```

(Substitute `NNNNN` literally in the jq path — Bugzilla keys comments by
the bug id as a string.)

## Method 3 — Web URL (last resort, when API is down)

Direct link to share with the user:
`https://bugs.koha-community.org/bugzilla3/show_bug.cgi?id=NNNNN`

## Output to user

Summarise the bug in 5–10 lines:
- **Bug NNNNN — `<summary>`** ([status, severity, component])
- **Reporter / Assignee**: who/who
- **Description**: first 2–3 sentences of comment 0 (the description),
  trimmed to readable length.
- **Test plan**: extract the section starting with `Test plan:` if present
  in the description.
- **Recent activity**: the last 1–2 comments, author + 1-line gist.

End with the bug URL. Don't dump the full comment thread — surface what
matters for starting work.

## Common failures

- **401/404 from REST API** — bug doesn't exist, or it's restricted (private
  security bug). Use Method 1 if `git bz` is configured.
- **Slow response** — bugs.koha-community.org is sometimes sluggish.
  Allow up to 30s before timing out.
- **Test plan missing** — many old bugs have no formatted test plan.
  Note this in the output rather than hallucinating one.
- **`git bz show` fails even though `~/.git-bz` looks populated** — check
  the tracker config, not just credentials: `git config
  bz-tracker.bugs.koha-community.org.path` and `.https` must be set (e.g.
  `/bugzilla3` and `true`). Missing tracker config is a separate failure
  mode from missing/stale auth.
