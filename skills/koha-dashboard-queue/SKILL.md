---
name: koha-dashboard-queue
description: Read a Koha dashboard queue or a user's dashboard section (Ready to push, Needs QA, Needs signoff, Failed QA, Patch doesn't apply, ...) from dashboard.koha-community.org through its JSON API, with the maintainer's personal Bugzilla API key, instead of copy/pasting the queue from the web page. Use when the user asks to "get/fetch/list the queue", "what's in Ready to push / Needs QA / Failed QA", or to work the dashboard's bugs in order. Arguments (optional): a queue name such as `needs-push`, or `user <id> <group>[/<section>]`.
---

Fetch a dashboard queue and present it, in the dashboard's order.

Arguments: $ARGUMENTS — optional. Examples:
- `needs-push` (or "ready to push") → `/api/queues/needs-push`
- `needs-qa`, `needs-signoff`, ... → the matching team queue
- `user 249 needs-work/failed-qa` → one section of a user's dashboard
- `user 249` → discovery: list that user's groups and sections
- empty → ask which queue (offer the list below)

## Pre-flight

**Key.** The dashboard identifies you by a personal Bugzilla API key. Create
one in Bugzilla under Preferences -> API Keys and export it in the shell
Claude Code runs in:

```bash
export KOHA_DASHBOARD_API_KEY=...   # the user does this, never Claude
```

Check it is set without showing it:

```bash
[ -n "$KOHA_DASHBOARD_API_KEY" ] && echo "key set" || echo "key missing"
```

If missing, say how to create one and carry on anonymously only if the user
agrees: without a key the dashboard answers as the public, so restricted
(security) bugs are absent and the list under-reports. Say so in the output.

**Host.** `KOHA_DASHBOARD_URL`, default `https://dashboard.koha-community.org`:

```bash
HOST="${KOHA_DASHBOARD_URL:-https://dashboard.koha-community.org}"
```

**Two credentials.** `git bz` (see `koha-bz-apply`, `koha-bz-fetch`) uses the
maintainer's Bugzilla login, not an API key. The dashboard needs this separate
API key. Never ask the user to paste either credential into the chat.

## Endpoints

Team queues (the dashboard's main page), all under `$HOST`:

| Endpoint | Dashboard section | Returns |
|----------|-------------------|---------|
| `/api/queues/needs-triage` | Needs triage | `{bugs, targeted}` |
| `/api/queues/needs-patches` | Needs patches | `{bugs, targeted}` |
| `/api/queues/needs-signoff` | Needs signoff | `{bugs, targeted}` |
| `/api/queues/needs-qa` | Needs QA | `{bugs, targeted}` |
| `/api/queues/needs-release-notes` | Needs release notes | `{bugs}` |
| `/api/queues/needs-documenting` | Needs documenting | `{bugs}` |
| `/api/queues/needs-push` | Ready to push (Passed QA) | `{bugs}` |
| `/api/queues/stats` | counts only, no bugs | `{status, bugs_only}` |

`targeted` holds bugs with a committed release target; the main list is
`bugs`. There is no team-wide "Failed QA" or "Patch doesn't apply" queue; use
the per-user endpoints.

Per user (`<id>` is the numeric Bugzilla user id):

| Endpoint | Returns |
|----------|---------|
| `/api/users/<id>/queues` | discovery: `{user, groups:[{slug, title, sections:[{slug, title, url}]}]}`, no counts |
| `/api/users/<id>/queues/<group>` | `{group, count, sections:[{slug, title, count, bugs}]}` |
| `/api/users/<id>/queues/<group>/<section>` | `{group, section, title, count, bugs}` |

Groups: `needs-work`, `claimed-qa`, `waiting`, `reported`, `cc`. Common
sections: `needs-work/failed-qa`, `needs-work/patch-doesnt-apply`,
`needs-work/needs-release-notes`, `waiting/needs-signoff`, `waiting/needs-qa`,
`waiting/ready-to-push`. Do not guess other slugs: call the discovery endpoint
(or read the "JSON API for queues" section of the dashboard `README`) and use
the slugs it returns. An unknown group or section answers `404`
`{"error":"unknown group"}` / `{"error":"unknown section"}`; a non-numeric or
unknown user answers `404 {"error":"user not found"}`.

If the user does not know their numeric id, ask for it (or for the profile URL
on bugs.koha-community.org); do not look for it in credential files.

## Fetch

One request, key from the environment, header `X-BUGZILLA-API-KEY` (not
`Authorization`: Apache can strip it). Never `set -x`, never `echo` the key,
never put it in a URL or query string, never write it to a file.

```bash
HOST="${KOHA_DASHBOARD_URL:-https://dashboard.koha-community.org}"
curl -sf -H "X-BUGZILLA-API-KEY: $KOHA_DASHBOARD_API_KEY" \
  "$HOST/api/queues/needs-push" > "$SCRATCH/queue.json"
```

Use the scratchpad (or another temp directory) for `$SCRATCH`; the JSON holds
bug data, not the key. Without a key (user agreed to anonymous), drop the `-H`
line. The same call works for `/api/users/<id>/queues/<group>/<section>`.

If it fails (non-zero exit), do **one** diagnostic request to read the status
and error body, then follow the error table below. Do not retry in a loop.

```bash
curl -s -w '\n%{http_code}\n' -H "X-BUGZILLA-API-KEY: $KOHA_DASHBOARD_API_KEY" \
  "$HOST/api/queues/needs-push"
```

## Read the result

Print the list in the order returned. The order of `bugs` is the dashboard's
importance order: never sort, group or reorder it (tell the user if they ask
for a different order, and keep the original numbering visible).

```bash
jq -r '.bugs | to_entries[] | .key as $i | .value
  | "\($i + 1). \(.bug_id) [\(.bug_severity)] \(.short_desc)"
    + ([ (if .roadmap_target then "target:\(.roadmap_target)" else empty end),
         (if (.missing_release_notes // 0) > 0 then "no-release-notes" else empty end),
         (if (.depends_on | length) > 0 then "deps:\(.depends_on | join(","))" else empty end),
         (if (.keywords | length) > 0 then "keywords:\(.keywords | map(tostring) | join(","))" else empty end)
       ] | if length > 0 then "  {" + join(" ") + "}" else "" end)' \
  "$SCRATCH/queue.json"
```

Count: `jq '.bugs | length' "$SCRATCH/queue.json"` (for a section response also
the `count` field; for a group response, each section has its own `count` and
`bugs`, so apply the recipe per section: `.sections[] | select(.slug=="...")`).

Fields on each bug (the dashboard's, not the full Bugzilla record):

| Field | Meaning |
|-------|---------|
| `bug_id` | Bugzilla bug number (a string in the JSON) |
| `short_desc` | summary |
| `bug_severity` | Bugzilla severity (blocker, critical, major, normal, minor, enhancement, ...) |
| `component_name`, `product_id` | component and product |
| `qa_contact` | QA contact (main queues, and the user groups except `claimed-qa`) |
| `assignee` | assignee (main queues, and `reported`, `claimed-qa`, `cc`; not `needs-work`/`waiting`) |
| `roadmap_target`, `target_milestone` | release the bug is targeted at, when set (`null` or `---` otherwise) |
| `keywords` | list of Bugzilla keyword **ids** (integers, not names); empty when none |
| `depends_on` | list of bug ids this bug depends on; `dep_count` (user queues) is how many |
| `missing_release_notes` | main queues: non-zero when release notes are still needed |
| `complexity`, `version` | main queues only: patch size label and Koha version |
| `bug_status` | status (user queues) |
| `bug_when` | creation time |
| `last_active_*`, `last_activity_*`, `last_comment_*` | user queues: time and user of the latest activity or public comment; `last_active_*` may be `null` (the viewed user touched the bug since) |

There are no comments, attachments or patches in the payload: use
`koha-bz-fetch` for those. Fields not present for a given queue are simply
absent; do not invent them.

## Errors

Visibility equals the key owner's Bugzilla visibility; a key that is presented
but unusable fails closed, it never falls back to anonymous.

| Response | Meaning | What Claude says and does |
|----------|---------|---------------------------|
| key missing | `KOHA_DASHBOARD_API_KEY` empty | Say how to create the key (Bugzilla Preferences -> API Keys) and export it; offer an anonymous (public bugs only) fetch, flagged as incomplete. Do not ask for the key in chat. |
| `401 {"error":"invalid API key"}` | key unknown, revoked, or its account disabled | Stop. Tell the user the key is not accepted: check it was copied fully and not revoked, create a new one in Bugzilla. Do not retry, do not print the key, do not silently fall back to anonymous. |
| `401 {"error":"conflicting API keys"}` | two different keys sent in the two supported headers | Stop. This skill sends one header; look for a proxy or wrapper adding `Authorization: Bearer`; ask the user to clear it. |
| `503 {"error":"API key lookup unavailable"}` | the dashboard cannot reach its key database right now | Tell the user it is a temporary dashboard problem; offer one later retry on their say-so, or an anonymous fetch flagged as incomplete. No retry loop. |
| `404` unknown user / group / section | wrong id or slug | Show the error text; call the discovery endpoint and offer the valid slugs. |
| `200` with empty `bugs` | the queue is empty (or nothing visible to this key) | Say "queue is empty" with the queue name; mention the visibility caveat if anonymous. Do not treat it as an error. |
| network failure, timeout, HTML or non-JSON body | dashboard down or unreachable | Report it once with the URL host and exit code; suggest checking connectivity or trying the web page. Do not retry in a loop. |

## Present

- One header line: queue name (or group/section and title), the count, and
  whether it was fetched with a key or anonymously.
- A numbered compact list in the returned order, one line per bug: id,
  severity, summary, then the flags from the recipe (target, no release notes,
  dependencies, keywords). Truncate very long summaries; do not print raw JSON
  or the full field set.
- If the response has `targeted`, mention how many there are but list only
  `bugs` unless the user asks for the targeted ones too.
- Offer to take the bugs one at a time, in that order, starting with the first
  (or the first N the user names). Do not start applying or reviewing anything
  until they say so.
- If a bug's `depends_on` lists bugs that are not in this queue, note it next
  to that bug and mention it before applying.

## Hand-off

Pick the next skill per bug, and do not run them automatically:

- `koha-bz-fetch` — the bug's description, test plan and recent comments.
- `koha-bz-apply` — apply the patches (with `Depends on` chain) to the worktree.
- `koha-review` — QA review of the applied patchset.
- `koha-qa` — the QA script in KTD.
- `koha-prove` — relevant tests in KTD.
- `koha-rm-queue` — for the "Ready to push" queue as a release manager: the
  loop that applies, reviews, signs off and pushes, with the maintainer gating
  each step. Hand over to it when the user wants to work that queue rather than
  just read it.

## Safety rules

- Never read, print, log or store the API key: no `set -x`, no `echo`/`printenv`
  of the variable, no key in a command shown back to the user (use the
  `$KOHA_DASHBOARD_API_KEY` variable name only), no key in files, commits or
  the chat. Do not look in `~/.git-bz`, git config or other files for a key.
- Read-only: this skill only issues GET requests to the dashboard. It never
  changes Bugzilla.
- A failed request is diagnosed once and reported; no retry loops.
- Keep the dashboard's order; present, do not reorder.
