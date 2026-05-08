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
docker exec --user kohadev-koha --workdir /kohadevbox/koha -i kohadev-koha-1 \
  bash -c '/kohadevbox/qa-test-tools/koha-qa.pl -v 2 --more-tests'
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
