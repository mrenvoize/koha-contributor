---
name: koha-review
description: "QA review a Koha patchset for regressions, security, code quality, and Koha-specific conventions. Use when the user says \"QA this\", \"review this patchset/branch/PR\", \"review my work\", or \"review N commits\". Auto-detects patchset scope, runs specialist review agents in parallel based on file types touched, compares behaviour across preference/configuration combinations before and after the patch when it changes settings-dependent behaviour, and synthesises findings into Critical/Important/Suggestion buckets with file:line citations."
---

QA-review a Koha patchset.

Arguments: $ARGUMENTS — optional. Examples:
- empty / "this branch" → diff `main..HEAD`
- "last 3 commits" → diff `HEAD~3..HEAD`
- "PR 4567" or "bug 33501" → resolve to a commit range (see Step 1)
- explicit range like `abc123..def456`

## Step 1 — Resolve the patchset scope

Decide the commit range from arguments. If unclear, default to `main..HEAD`
(Koha community uses `main`, not `master`).

```bash
git log --oneline <range>
git diff --stat <range>
git diff --name-only <range>
```

Show the user the resolved range (commit count, files changed, +/- lines)
in **one line** and proceed without confirmation unless the range is empty
or absurdly large (>50 files).

If the range is empty: stop and tell the user.

If `main..HEAD` fails with exit 128 / "unknown revision" — common in a
`git worktree` off a shared bare clone — check `git remote -v` and retry
with `upstream/main..HEAD` (or whatever the actual remote is called)
instead of assuming `main` resolves.

## Step 2 — Categorise touched files

Bucket the changed paths so we can target review correctly:

| Bucket | Glob hints |
|--------|------------|
| Perl modules | `Koha/**.pm`, `C4/**.pm` |
| REST controllers | `Koha/REST/V1/**.pm` |
| Swagger / OpenAPI | `api/v1/swagger/**.yaml` |
| Templates | `koha-tmpl/**/*.tt`, `**/*.inc` |
| Vue / JS | `**/*.vue`, `**/*.js`, `**/*.ts` |
| SCSS / CSS | `**/*.scss`, `**/*.css` |
| SQL schema | `installer/data/mysql/kohastructure.sql` |
| Atomicupdates | `installer/data/mysql/atomicupdate/*.pl` |
| DBIC schema | `Koha/Schema/Result/*.pm` |
| Sysprefs UI | `**/admin/preferences/*.pref` |
| Tests | `t/**.t`, `t/cypress/**` |
| Docs | `**.md`, `*.pod`, `about.tt` |

Flag if any change set is suspicious on its own (e.g. `kohastructure.sql`
without an atomicupdate, swagger change without a controller change, new
`.pm` without tests).

## Step 3 — Recommend automated checks first

Before LLM review, encourage running the deterministic checks:

- If touched: Perl/SQL → suggest `koha-qa` skill (runs `koha-qa.pl`).
- If touched: tests → suggest `koha-prove` for those test files.
- If touched: SCSS/Vue/Swagger → suggest `koha-build`.
- If touched: atomicupdate / kohastructure → suggest `koha-schema-apply` if
  not yet applied.

- If the patch changes behaviour or a UI flow that depends on preferences or
  rules: Step 7 (configuration combinations), and `koha-review-walkthrough`
  for side-by-side before/after videos.

Don't run them automatically — they may already have. Just note which are
appropriate and let the user trigger them. When you do read their output, grep
it for warnings (`uninitialized` etc.): a warning the patch introduces is at
least **Important**, because any test that renders that path under
`Test::NoWarnings` will fail CI (see `koha-qa`).

## Step 4 — Spawn specialist agents in parallel

Pick agents based on the file buckets. Send all picked agents in a single
message (parallel tool calls). Pass each agent the explicit commit range,
the relevant file list, and a focused brief.

| Buckets touched | Agent to spawn | Brief focus |
|-----------------|----------------|-------------|
| Any Perl modules | `koha-perl-reviewer` | Koha conventions: modern Koha::* vs legacy C4::*, DBIC vs raw DBI, error handling, POD on public subs |
| REST controllers OR swagger | `pr-review-toolkit:code-reviewer` | Permissions on each endpoint, request/response schema match, error responses, OpenAPI doc parity |
| Atomicupdates / SQL schema | `koha-perl-reviewer` (separate call) | Idempotency (`column_exists`, `INSERT IGNORE`), `chmod +x`, `Koha::Installer::Output` usage, `tinyint(1)` boolean flag handling |
| Tests | `pr-review-toolkit:pr-test-analyzer` | Coverage for new code, edge cases, golden path; for `.t` files: `use Test::NoWarnings`; for Cypress: no `.only`/`.skip` left in |
| Any code with try/catch / fallbacks | `pr-review-toolkit:silent-failure-hunter` | Suppressed errors, silent fallbacks, lost context |
| New types / classes / hashref shapes | `pr-review-toolkit:type-design-analyzer` | Encapsulation, invariants, useful abstractions |
| Auth, permissions, input handling, file uploads, SQL building | `security-review` skill **or** `pr-review-toolkit:code-reviewer` with security focus | XSS in templates, SQLi in raw DBI, missing permission checks, CSRF |
| Significant comment additions or doc edits | `pr-review-toolkit:comment-analyzer` | Accuracy, decay risk, references to current state |

Pick the handbook docs from Step 5 first, so each brief can name them.
Each agent runs read-only. If unavailable, fall through to direct review by
the model itself for that bucket.

**Known gap:** an automated pass like this one is weaker than an
interactive human reviewer at catching two things in particular —
issues in a "Depends on" bug that hasn't landed yet (transitive
dependencies), and whether backend behaviour actually matches what the
patch claims (as opposed to matching it on paper). Call this out in the
final summary rather than presenting automated coverage as equivalent to
a full interactive review.

## Step 5 — Handbook conventions (model performs, and briefs agents with)

The vendored koha-handbook is the source of truth for conventions: it
changes upstream and is re-synced weekly, so **do not restate its rules in
this skill** — read the relevant docs and review against them. The handbook
lives at `${CLAUDE_PLUGIN_ROOT}/references/koha-handbook/` (if that path is
missing, e.g. skills copied without the plugin, say so in the summary and
rely on the checks below).

Read only the docs matching the buckets from Step 2, and pass the same
paths to each specialist agent in Step 4 so they check against them too:

| Buckets touched | Handbook docs |
|-----------------|---------------|
| Any Perl | `coding_guidelines.md` |
| `Koha::Object(s)` classes, DBIC schema | `koha_objects_system.md`, `database_naming_conventions.md` |
| REST controllers / Swagger | `coding_guidelines_api.md`, `koha_rest_api_architecture.md` |
| Templates | `koha_template_toolkit.md`, `coding_guidelines.md` (Templates, Security) |
| SQL schema / atomicupdates | `database_naming_conventions.md`, `coding_guidelines.md` (Database) |
| Tests | `koha_testing_framework.md` |
| Background jobs | `background_jobs.md` |
| Plugin code | `plugin_architecture.md` |
| New abstractions | `koha_design_patterns.md` and `patterns/*.md` |

If a touched area has no doc here, grep the handbook (`README.md` is the
index) before concluding there is no convention. Cite findings with the
doc and section (e.g. `koha_objects_system.md`, "Standard POD for `_type`
and `object_class`"). A handbook rule is **Important** unless the doc says
otherwise.

## Step 6 — Direct Koha-specific checks (model performs)

While agents run (or after, if you can't run in parallel), the model does
these checks directly. These cover what the handbook doesn't, or what is
cheap to verify mechanically:

### Bug branch / commit hygiene
- Each commit subject starts with `Bug NNNNN: ` (Koha convention).
- No fixup/squash commits left in the range.
- Commit messages explain WHY, not just WHAT.

### Modern vs legacy
- New `.pm` should be in `Koha/`, not `C4/`. New code in `C4/` needs strong justification.
- New code uses DBIx::Class (`Koha::Foos->search(...)`) not raw DBI (`$dbh->prepare`).
- Avoid `GetMember`, `ModMember`, etc. — use `Koha::Patrons->find->update`.

### Templates (TT)
- All user-controlled output is escaped: `[% var | html %]` (or `| uri` in URLs).
- `FILTER none` only with explicit justification (e.g. pre-rendered HTML).
- New strings are translatable: wrapped or inside template blocks the
  translation extractor sees.
- Never `[% SET x = rs.as_list %]` and then call `x.size`/`x.count`. Template
  Toolkit unwraps a one-element list to the bare `Koha::Object`, so it works
  for 0 and 2+ rows and breaks for exactly 1 (an AUTOLOAD "method not covered
  by tests" error at render time, which `prove` never sees). Iterate directly
  (`FOR i IN rs.as_list`) or call `.count` on the resultset itself.

### Vue / JS
- New components use Vue 3 Composition API (`<script setup>`).
- No jQuery inside Vue components.
- User-visible strings use `$_()` (vue-i18n) — not hard-coded English.

### REST controllers
- Each endpoint specifies `permissions` correctly in `api/v1/swagger/paths/*.yaml`.
- Response schema matches what the controller returns (no extra/missing fields).
- Error responses use `$c->render_resource_not_found`, `$c->render_invalid_parameter_value`, etc., not ad-hoc JSON.

### Database / migrations
- `kohastructure.sql` change has a corresponding atomicupdate.
- Atomicupdate is idempotent: `column_exists`, `INSERT IGNORE`, etc.
- Atomicupdate file is `chmod +x` (`git ls-files --stage` shows mode 100755).
- Atomicupdate uses `Koha::Installer::Output` helpers, not bare `say $out`.
- New `tinyint(1)` columns: if semantically yes/no, add `is_boolean => 1` BELOW the `# DO NOT MODIFY` line in the Result module.
- DBIC `Result/*.pm` changes only auto-generated portions came from `dbic --force` (auto changes in their own commit), with manual edits (relations, `is_boolean`, `koha_object_class`) BELOW the marker in a separate commit.

### Tests
- New `Koha::Foo` module has a corresponding `t/Koha/Foo.t`.
- New REST endpoint has a corresponding `t/db_dependent/api/v1/*.t`.
- New UI feature has a Cypress spec.
- Test files have `use Test::NoWarnings;` at the top.
- A patch that adds or retypes a column: every existing
  `TestBuilder->build({ source => '<Table>' })` that a new read path depends on
  must pin the column (TestBuilder fills unset columns with type-based random
  values and "now" for datetimes; see `koha-schema-apply`).
- Does the test toggle every preference/rule the new code reads (Step 7)? A
  setting read by new code that no test varies is an **Important** gap.

### Test plans in the commit message
- Steps are librarian-facing UI steps (page, click, expected result), with
  `prove` only as an extra. A `prove`-only plan is **Important**.
- Security fixes: the plan must reproduce through the browser or `curl` with
  before, after and a control, not just automated tests (`koha-security-verify`).

### System preferences
- New syspref has: an atomicupdate INSERT, a row in `installer/data/mysql/mandatory/sysprefs.sql` (alphabetical; missing it means fresh installs lack the pref), an entry in the right `.pref` file, a default value, a type, an explanation.
- Default behaviour preserves existing behaviour (don't change defaults silently).

### API contract evolution
- Don't add parallel fields when an existing field can evolve — match
  existing API contract idioms.
- Breaking changes (renamed/removed fields) need a deprecation path or are flagged in commit message.
- If the range includes a merge/rebase that resolved a conflict against
  another in-flight bug touching the same API client or registration
  point, check for leftover duplicates — conflict resolution can keep
  both sides' additions (e.g. two client instances registered for the
  same resource) instead of consolidating to one. Look for a later
  "consolidate" commit as a signal this already bit the author once.

## Step 7 — Configuration combinations ("actions at a distance")

A patch is rarely wrong in the default configuration. It goes wrong when a
preference, circulation rule, library or category setting, permission or
interface that the **old** code honoured is no longer consulted, or when two
settings that gate the same decision interact differently. Run this step when
the patch changes behaviour or a UI flow that reads settings; skip it for
docs, pure refactors that keep tests green, and schema-only changes.

1. **List the inputs on both sides.** For the touched functions, templates
   and the code they call or replace, collect every setting read, before
   (`main`) and after (patched): `C4::Context->preference('X')`,
   `Koha.Preference('X')` in templates, `Koha::CirculationRules`
   (`get_effective_rule`), branch/category/itemtype-specific values, library
   groups and `IndependentBranches`, permissions, staff vs OPAC, plugin hooks,
   `koha-conf.xml` keys. Present a small table: setting, read by old, read by
   new, verdict.
   - Read by old only → **dropped**: the likeliest regression. Is the
     removal deliberate and stated in the commit message?
   - Read by new only → new behaviour: does its default preserve today's?
   - Read by both → check the semantics match for every value.
2. **Choose combinations.** Always: baseline (defaults); each related setting
   flipped alone; and the combinations where two settings gate the same
   decision (e.g. `AutomaticItemReturn` x `TransfersBlockCirc` x
   `AutomaticConfirmTransfer`). Use pairwise coverage, not the full product,
   and keep it to roughly 25 scenarios; say what was left out.
3. **Compare before and after with identical data.** Same seed, settings and
   barcodes on an unpatched instance (a worktree of `main`, or the base the
   series was built on) and the patched one. Backend: loop the combinations in
   a Perl test with `t::lib::Mocks::mock_preference` and compare return
   values and DB rows. UI flow: `koha-review-walkthrough` records matching
   videos per combination and a side-by-side player. Compare the **database
   outcome** first (item state, fines, transfers, holds, messages), then the
   flow and wording.
4. **Classify each difference:** same; UI differs but outcome same (usually
   Suggestion unless intentional); **outcome differs** (Critical or Important
   unless the bug intends it); possible only after (check it is gated by the
   right setting). Check the same for main-vs-main first: a "regression" that
   also happens on `main` is not the patch's fault - say so.
5. **Leave the instance as you found it.** Restore every preference you
   changed and note any you flipped by accident; leftover settings leak into
   later `prove` runs.

Report the matrix in the findings (setting combination, old outcome, new
outcome, verdict). If time doesn't allow it, say which combinations were not
exercised instead of implying coverage.

## Step 8 — Synthesise findings

Merge agent reports + direct checks. Deduplicate. Bucket as:

- **🔴 Critical** — security issue, regression, broken build, data corruption risk, or QA-blocker (e.g. atomicupdate not executable). Must fix before submission.
- **🟡 Important** — convention violation, missing test, escaping gap that's not currently exploitable, missing POD, accessibility regression. Should fix.
- **🔵 Suggestion** — refactor opportunity, simplification, naming nit. Nice to have.

For each finding, give:
- File and line (`path/to/file.pm:42`)
- One-line description of the issue
- WHY it matters (1 sentence, not a lecture)
- Concrete suggested fix or pointer to the right pattern

Group by file when there are multiple findings in the same file.

## Step 9 — Verdict

End with one of:

- **PASS** — no Critical, ≤ 2 Important. Ready to submit.
- **PASS WITH CHANGES** — no Critical, but several Important. Fix before submitting.
- **REQUEST CHANGES** — at least one Critical. Don't submit until fixed.

Then a one-paragraph summary: total commits, total files, total findings
by bucket, and the top 1–3 things to fix first.

## Notes

- This skill is for review, not for making changes. Don't auto-fix issues
  unless the user explicitly asks.
- When reviewing your OWN work, be more critical, not less. Self-review is
  most valuable when it surfaces things external QA would catch.
- If the patchset is huge (>30 files or >2000 LOC), warn the user that
  review quality degrades; suggest splitting the patchset by feature.
