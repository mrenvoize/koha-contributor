---
name: koha-qa
description: Run the Koha QA script (koha-qa.pl) inside KTD before submitting patches. Surfaces critic, POD, file_permissions, tinyint_has_boolean_flag, and other QA failures the community reviewers will check. Run after every commit; fix flagged issues before pushing.
---

Run the Koha QA script against the current branch.

Arguments: $ARGUMENTS (optional — defaults to checking the commit range against `main`)

## Pre-flight

Changes must be **committed**, not just staged. The QA script reads
`git diff HEAD` against earlier commits. If the working tree is dirty, ask
the user to commit first.

```bash
git status --porcelain
```

If output is non-empty, stop and tell the user.

## Run

```bash
ktd --name "${KTD_INSTANCE:-kohadev}" --shell --run '/kohadevbox/qa-test-tools/koha-qa.pl -v 2 --more-tests'
```

`-v 2` is the recommended verbosity. `--more-tests` enables the slower
checks (POD coverage, spelling, etc.) that community QA also runs.

## Interpret results

The script reports per-commit. Triage flagged issues into:

### Real failures to fix

- **`file_permissions`** — `chmod +x` test files AND atomicupdate files
  (`installer/data/mysql/atomicupdate/bug_*.pl` MUST be executable).
- **`test_no_warnings`** — add `use Test::NoWarnings;` to the test file.
- **`forbidden_patterns`** — avoid raw `http://` in code (split as
  `'http' . '://...'` for W3C namespace URIs); also check comments.
- **`pod_coverage`** — every public `sub` needs a `=head3` POD block.
- **`critic` severity 5** — common: variable declared in conditional
  (`my $x = ... if $cond` → declare outside).
- **`spelling`** — typos in strings/comments.
- **`tinyint_has_boolean_flag` (SQL12)** — handle by **column semantics**:
  - **Yes/no flag** → add `'+colname' => { is_boolean => 1 }` to an
    `__PACKAGE__->add_columns(...)` block BELOW the
    `# DO NOT MODIFY THIS OR ANYTHING ABOVE!` line in the Result module.
    `dbic --force` preserves content there.
  - **Genuine small integer** (rare) → leave as-is, do NOT add
    `is_boolean` (DBIC would decode wrong), do NOT widen to `tinyint(4)`.
    Call this out explicitly in the commit message so reviewers don't
    flag the QA warning.

### Known KTD environment limitations (NOT real failures — ignore)

- **Vue/JS `tidiness`** — `prettier` is not in `$PATH` in KTD. To format,
  run `/kohadevbox/node_modules/.bin/prettier --write <file>` then verify.
- **`Bad plan` from `skip_all` + `Test::NoWarnings`** — when a test does
  `plan skip_all` because an optional module isn't installed,
  `Test::NoWarnings`' END block still runs and reports a bad plan. Harmless
  on machines that have the module.

### Known false positives (verify, then work around)

- **`forbidden_patterns` scans every changed file, not just Perl.** A literal
  `_(` in a Cypress `.ts` payload (e.g. a crafted malicious parameter name
  such as `filter_(SELECT(1))_begin`) is flagged as the Perl gettext rule.
  Rephrase the payload (a quote-based SQLi shape like `' OR '1'='1` works);
  the test's point doesn't depend on parentheses.
- **`git_manipulation`** fires when a follow-up commit renames or moves a
  file added by the previous commit in the range. Don't move files in QA
  follow-ups; keep them small.
- **The worktree pre-commit hook** rejects tabs in `debian/rules` (a Makefile,
  tabs are required) and added lines containing `warn` in `debian/scripts/*`
  (the shell helper, not Perl's `warn`). For commits touching only those, use
  `git commit --no-verify`, say so in the summary, and let `koha-qa.pl` be the
  real check.
- **`prettier --write` on a `.tt` file can corrupt unrelated markup** (it once
  commented out a real `</head>`/`<body>` pair in `auth.tt`). `git diff` after
  running it on any template and hand-revert everything outside your hunk.

### Warnings are findings

Don't wave a warning through as "non-blocking". Grep the QA and test output for
`uninitialized` and other warnings. A warning your patch introduces breaks CI
as soon as any test renders that path under `Test::NoWarnings` (bug 43782 was
pushed with "uninitialized $session_id" noted as cosmetic, then failed
`t/db_dependent/Koha/Plugins/TemplateIncludePathHook.t`). For template or
plugin-hook changes also run `prove -r t/db_dependent/Koha/Template
t/db_dependent/Koha/Plugins`. If the warning pre-dates the patch, say so.

## Atomicupdate output conventions (related, often flagged together)

Use `Koha::Installer::Output qw(say_success say_warning say_failure say_info)`:

- `say_success($out, "...")` — step completed
- `say_warning($out, "...")` — already-applied step (e.g. `column_exists`)
- `say_failure($out, "...")` — hard failure
- `say_info($out, "...")` — informational

Idempotent column-add pattern:
```perl
if ( column_exists($table, $col) ) {
    say_warning($out, "Column '$table.$col' already exists, skipping.");
} else {
    $dbh->do(q{ALTER TABLE ...});
    say_success($out, "Added column '$table.$col'");
}
```

## Output to user

Summarise as: per-commit pass/fail counts, the categories of issues found,
and a short remediation list. Don't dump the full QA output — pull out the
first failing line per category, the user can re-run for full detail.
