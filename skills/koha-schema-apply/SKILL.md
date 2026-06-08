---
name: koha-schema-apply
description: Apply a Koha DB schema change end-to-end after editing kohastructure.sql and the atomicupdate file. Runs updatedatabase.pl in KTD, regenerates DBIC schema with dbic --force, and reminds about the manual is_boolean / relationship edits below the marker line. Use this after the atomicupdate skill has scaffolded the file and the SQL is filled in.
---

Apply a Koha DB schema change end-to-end.

Arguments: $ARGUMENTS (optional — bug number, used in commit message suggestions)

## Pre-flight

This skill assumes:
- `installer/data/mysql/kohastructure.sql` has been updated.
- `installer/data/mysql/atomicupdate/bug_NNNNN.pl` exists, is executable
  (`chmod +x`), and contains the SQL.
- The atomicupdate file uses `Koha::Installer::Output` helpers.

If any of these isn't true, stop and tell the user what's missing — the
`atomicupdate` skill handles scaffolding, this skill handles applying.

## Step 1 — Run the atomicupdate

```bash
ktd --name "${KTD_INSTANCE:-kohadev}" --shell --run 'perl installer/data/mysql/updatedatabase.pl'
```

Expect to see the `say_success` / `say_warning` lines from the atomicupdate.
If the script errors (typically SQL syntax or connection issues), stop and
surface the error — do NOT continue to dbic regeneration on a broken DB.

## Step 2 — Regenerate DBIC schema

```bash
ktd --name "${KTD_INSTANCE:-kohadev}" --shell --run 'dbic --force'
```

This rewrites the auto-generated portions of `Koha/Schema/Result/*.pm`.
NEVER edit those portions by hand.

## Step 3 — Add manual annotations BELOW the marker

`dbic --force` preserves content **below** the `# DO NOT MODIFY THIS OR
ANYTHING ABOVE!` line in each Result module. Add the following there, NOT
above.

### Boolean flag columns (SQL12 / `tinyint_has_boolean_flag`)

For every new `tinyint(1)` column that **semantically represents a yes/no
flag**, add:

```perl
__PACKAGE__->add_columns(
    '+colname' => { is_boolean => 1 },
);
```

If the column is genuinely a small integer (rare), leave it alone, do NOT
add `is_boolean`, do NOT widen to `tinyint(4)`. Mention this explicitly in
the commit message so QA reviewers don't flag the warning.

### Pseudo `belongs_to` (no real SQL FK)

When adding a `belongs_to` relation that does NOT have a real SQL foreign
key, you MUST set `is_foreign_key_constraint => 0` — otherwise TestBuilder
breaks for the parent class.

```perl
__PACKAGE__->belongs_to(
    "thing" => "Koha::Schema::Result::Thing",
    { id => "thing_id" },
    { is_foreign_key_constraint => 0, ... },
);
```

### Object class aliases

```perl
sub koha_object_class  { 'Koha::Foo'  }
sub koha_objects_class { 'Koha::Foos' }
```

## Step 4 — Commit in two parts

Convention:

1. **First commit**: only the auto-generated DBIC changes from `dbic --force`,
   subject `Bug NNNNN: Automated Schema Update`.
2. **Second commit**: the manual additions below the marker (is_boolean,
   relations, koha_object_class), with a descriptive subject.

This keeps the auto-generated diff reviewable on its own.

## Output

Report:
- Atomicupdate output (success/warning lines).
- Files changed by `dbic --force` (`git status` after step 2).
- Reminder of the manual edits the user still needs to apply, with file
  paths to the relevant Result modules.
