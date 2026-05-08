---
name: koha-review
description: QA review a Koha patchset for regressions, security, code quality, and Koha-specific conventions. Use when the user says "QA this", "review this patchset/branch/PR", "review my work", or "review N commits". Auto-detects patchset scope, runs specialist review agents in parallel based on file types touched, and synthesises findings into Critical/Important/Suggestion buckets with file:line citations.
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

Don't run them automatically — they may already have. Just note which are
appropriate and let the user trigger them.

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

Each agent runs read-only. If unavailable, fall through to direct review by
the model itself for that bucket.

## Step 5 — Direct Koha-specific checks (model performs)

While agents run (or after, if you can't run in parallel), the model does
these checks directly. These are the things a generic code reviewer
won't catch:

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

### System preferences
- New syspref has: an atomicupdate INSERT, an entry in the right `.pref` file, a default value, a type, an explanation.
- Default behaviour preserves existing behaviour (don't change defaults silently).

### API contract evolution
- Don't add parallel fields when an existing field can evolve — match
  existing API contract idioms.
- Breaking changes (renamed/removed fields) need a deprecation path or are flagged in commit message.

## Step 6 — Synthesise findings

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

## Step 7 — Verdict

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
