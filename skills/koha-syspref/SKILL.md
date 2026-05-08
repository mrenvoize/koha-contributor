---
name: koha-syspref
description: Add a new Koha system preference. Generates the atomicupdate INSERT and edits the matching admin/preferences/*.pref YAML so the syspref appears in the staff UI. Arguments: bug number, preference name, and a hint about which preferences page (e.g. patrons, circulation, opac).
---

Scaffold a new Koha system preference end-to-end.

Arguments: $ARGUMENTS — expected: `<bug-number> <PrefName> <category-hint>`

## Pre-flight

If the user supplied only a name and no category, ask which `.pref` file
the syspref belongs in. Common values:

| Category hint | File |
|---------------|------|
| `patrons` | `koha-tmpl/intranet-tmpl/prog/en/modules/admin/preferences/patrons.pref` |
| `circulation` | `.../admin/preferences/circulation.pref` |
| `cataloguing` | `.../admin/preferences/cataloguing.pref` |
| `opac` | `.../admin/preferences/opac.pref` |
| `i18n` / `l10n` | `.../admin/preferences/i18n_l10n.pref` |
| `acquisitions` | `.../admin/preferences/acquisitions.pref` |
| `admin` | `.../admin/preferences/admin.pref` |

If none of these fit, list the directory:
```bash
ls koha-tmpl/intranet-tmpl/prog/en/modules/admin/preferences/
```

Also gather: type (`YesNo`, `Choice`, `Integer`, `Textarea`, `free`),
default value, and the option list if `Choice`.

## Step 1 — Atomicupdate INSERT

If no atomicupdate file exists for this bug, create one (defer to the
`atomicupdate` skill or scaffold inline).

Add an INSERT to the atomicupdate's `up` sub:

```perl
$dbh->do(q{
    INSERT IGNORE INTO systempreferences (variable, value, options, explanation, type)
    VALUES (
        'PrefName',
        'defaultvalue',
        'option1|option2',
        'Explanation shown in admin UI.',
        'Choice'
    )
});
say_success($out, "Added system preference 'PrefName'");
```

Notes:
- `INSERT IGNORE` makes the atomicupdate idempotent (re-running it does
  nothing rather than failing on duplicate key).
- `options` is `NULL` (or omit) for non-Choice types.
- `type` is one of `YesNo`, `Choice`, `Integer`, `Textarea`, `free`,
  `Float`, `Upload`, `Lang`, `Date`.

## Step 2 — Add to the .pref YAML

Open the chosen `.pref` file and add an entry under an appropriate section.
The `.pref` files use Koha's bespoke YAML-ish format. A typical entry:

```yaml
    -
        - "Display this label in the admin UI"
        - pref: PrefName
          choices:
              "option1": "Human-readable option 1"
              "option2": "Human-readable option 2"
        - "trailing label text (optional)."
```

For YesNo:
```yaml
    -
        - pref: PrefName
          choices:
              yes: Do
              no: "Don't"
        - "trailing context."
```

For Integer / free:
```yaml
    -
        - "Set the limit to"
        - pref: PrefName
          class: integer
        - "items."
```

Match indentation exactly — these files are whitespace-sensitive.

## Step 3 — Verify

After both edits:
1. Run the atomicupdate via the `koha-schema-apply` skill (or
   `perl installer/data/mysql/updatedatabase.pl` directly).
2. Load the admin preferences page in the browser and confirm the new
   syspref appears with the expected widget and default.
3. Run `koha-qa` — `.pref` files have their own QA checks.

## Output

Report:
- Atomicupdate file path + the INSERT block added.
- `.pref` file path + the entry added.
- Reminder to apply via `koha-schema-apply` and verify in the admin UI.
