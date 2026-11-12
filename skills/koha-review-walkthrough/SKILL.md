---
name: koha-review-walkthrough
description: "Record side-by-side before/after Playwright walkthrough videos of a Koha UI patchset across different preference and configuration combinations, plus a compare player and a results table. Use when reviewing or QAing a patch that changes a UI flow or behaviour governed by system preferences or circulation rules, when the user asks for walkthrough videos, a before-and-after comparison, or a browser-test prompt for a bug, or from koha-review Step 7. Arguments (optional): bug number and the settings or scenarios to cover."
---

Record matching before/after videos for each scenario and settings combination,
verify the database outcome for each, and build a player that puts them side by
side. The goal is to spot what a patch series changed **at a distance**: the
same action under the same settings behaves differently before and after.

Arguments: $ARGUMENTS

Companion files (in `${CLAUDE_PLUGIN_ROOT}/skills/koha-review-walkthrough/`, or
`~/.claude/skills/koha-review-walkthrough/` for a manual install): `driver.js`
(Playwright template), `build-driver.py`, `make-compare.py`,
`scenarios.example.json`.

## When to use it

Use it when the patch changes what a user sees or what happens after a click,
and that depends on settings (preferences, circulation rules, library or
category, permissions). Not worth it for backend-only changes (loop
`t::lib::Mocks::mock_preference` in a Perl test instead, see `koha-review`
Step 7), docs, or one-setting cosmetic changes. Recording is slow; agree the
scenario list with the user first.

## Step 1 - Two instances, same data

- **After:** the patched instance (the bug's worktree and KTD, `koha-workflow`).
- **Before:** an instance of the base the series was built on (the commit the
  patches apply to), in its own worktree, e.g. `kd up walk_main`. Never use the
  user's own `main` instance, and don't change anything on it by hand.
- Seed both with the **same** script, run id and barcodes (e.g.
  `WT<run>-<ID>`), through `Koha::` objects or `t::lib::TestBuilder` in the
  container. Items can usually be checked in or out once, so reseed with a new
  run id before every recording round, and keep the seed output as
  `manifest.json`.
- Both need `RESTBasicAuth=1` if you look items up through the API.
- The before instance has no new columns or tables from the series. Write the
  DB verification queries to tolerate that (check the column exists), or they
  fail only on the unpatched side.

## Step 2 - Define the scenarios

Work in `core/notes/<bug>-walkthrough/` (outside the repo; never commit it).
Copy `scenarios.example.json` to `scenarios.json` there and fill it in:

- `root` (absolute path of that directory), `sides.before/after` (`base` URL
  from `ktd --list`, label, colours), `baselinePrefs`.
- One entry per scenario: `title`, `pre` (situation), `what` (what it shows),
  `prefs` (settings that differ from baseline), `section`, and `steps`, or
  `steps_before`/`steps_after` when the two pages' selectors differ.

Scenario IDs: **S** = one pass of a distinct case (plain, overdue, lost, hold,
bundle, claim ...), **V** = variants that click each dialog option and end on
Koha's own view of the result (holdings Status, holds list).

Choose settings combinations as in `koha-review` Step 7: baseline, each related
setting alone, and every set of settings that gate the same decision. Group
scenarios by settings so each group needs one set-up. Set them in the container,
e.g. `perl -MC4::Context -e 'C4::Context->set_preference("X", 0)'`, then
`restart_all` if a Perl path caches them. Restore the baseline after every group.

### Step types

Each step is an object; combine keys in one step (they run in this order):
`caption`, `goto` (+ `waitFor`), `type` (selector, with `text`, `clear`),
`click` (selector; add `"nav": true` when the page navigates, as legacy Koha
pages do), `press` (key), `waitForSelector`, `wait` (ms), `observe` (label;
records URL, open modal title and buttons, first table rows via `rows`,
extra `text` selectors, then pauses so the result can be read).
Playwright selector syntax works, e.g. `.modal.show button:text-matches('^Yes','i')`.

Make sure the scenario shows the **result in Koha**, not only the dialog: end on
the holdings table or holds list, as the 42383 variants did.

## Step 3 - Record each side

```bash
S=core/notes/<bug>-walkthrough
python3 ${CLAUDE_PLUGIN_ROOT}/skills/koha-review-walkthrough/build-driver.py \
  $S/scenarios.json after <workspace>/.playwright-mcp/wt-after.js S01 S02
```

Then call the Playwright MCP tool `browser_run_code_unsafe` with
`filename: <workspace>/.playwright-mcp/wt-after.js`, and repeat with `before`.
Videos land in `<root>/<side>/<ID>/page@*.webm`; save the returned JSON as
`verify-<side>.json`.

Gotchas that cost time on bug 42383:

- The MCP only reads code files under its allowed roots (normally the session's
  workspace root), and its sandbox has no `require`, `import` or file access.
  That is why the config is injected into the file. If access is denied, put the
  generated file under the workspace root.
- Record a calibration scenario first (S01) and watch it. Fixed pauses make a
  video followable, but too long wastes minutes per scenario.
- 1920x1080 matters: at 1280 a wide check-in table clipped its Status column.
- Playwright needs a matching `ffmpeg-<n>` under `~/.cache/ms-playwright`. If
  recording fails with a missing ffmpeg, install the version it names (a symlink
  from an older one was only a stop-gap).
- A first take can fail (a missed confirmation click, a dialog covering the
  button). Fix the steps and re-record; the player uses the **newest** take, so
  delete bad ones.
- Legacy pages reload on every action; the driver keeps the caption in
  `sessionStorage` for that reason. Vue pages don't navigate, so don't set `nav`.
- Verify the database after each scenario (item status, fines, transfers, holds,
  claims, messages) through `ktd --name <name> --shell` or the REST API, and
  store it in `verify-before.json` / `verify-after.json`. The **DB outcome** is
  the finding; the video shows the flow.

## Step 4 - Compare and report

Fill in `tag` (`same`, `differs`, `new` = only possible after) and `note` per
scenario in `scenarios.json` from what you saw and the two `verify-*.json`
files, then:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/koha-review-walkthrough/make-compare.py core/notes/<bug>-walkthrough
```

Open `compare/index.html` (or `python3 -m http.server` in the directory and open
`/compare/` if the browser blocks local video). It has side-by-side, stacked and
one-after-the-other layouts, sync play, a dot per scenario, and keys
(`Space`, `R`, `S`, arrows, `[` `]`).

Write `README.md` in the same directory: a results table (ID, case, settings,
observed), outcome-identical or not, UI differences, things not covered, and
the real findings. Feed the `differs` ones into `koha-review` Step 7's
classification. Check each suspected regression against `main` before
blaming the patch: if the unpatched page does the same, say so.

Optionally add a "prompt for a browser session" to the README so a human or
another agent can reproduce each scenario by hand (URL, login, baseline
settings, per-scenario settings and expected result).

## Step 5 - Leave things as found

- Restore every setting you changed; list any you flipped by accident.
- The videos are large (the 42383 set was ~430MB): keep them in `core/notes/`,
  don't commit them and don't attach them to Bugzilla. Share through a hosted
  copy only if the user asks.
- Tear down the `before` instance and worktree (`kd down walk_main`) only when
  the user says so; `kd down --rm=full` also deletes the branch, so confirm.
