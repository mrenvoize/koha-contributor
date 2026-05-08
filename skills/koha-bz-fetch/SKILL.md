---
name: koha-bz-fetch
description: Fetch a Koha Bugzilla bug's summary, description, status, and recent comments from bugs.koha-community.org by bug number. Use before starting work on a bug to surface the test plan and any prior discussion. Argument: a Koha bug number (e.g. 33501).
---

Fetch a Koha Bugzilla bug by number.

Arguments: $ARGUMENTS — a single bug number (e.g. `33501`).

## Pre-flight

Validate the argument is a positive integer. If the user passed a URL like
`https://bugs.koha-community.org/bugzilla3/show_bug.cgi?id=NNNNN`, extract
the number from the `id` parameter.

## Method 1 — git bz (preferred if available)

If `git bz` is configured (`~/.git-bz` exists), use it:

```bash
git bz show NNNNN
```

This dumps the bug header, full description, and recent comments to stdout
using the user's authenticated session — works for restricted bugs too.

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

- **404 from REST API** — bug doesn't exist, or it's restricted (private
  security bug). Fall back to Method 1 if `git bz` is configured.
- **Slow response** — bugs.koha-community.org is sometimes sluggish.
  Allow up to 30s before timing out.
- **Test plan missing** — many old bugs have no formatted test plan.
  Note this in the output rather than hallucinating one.
