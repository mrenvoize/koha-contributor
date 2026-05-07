---
name: atomicupdate
description: Create a new Koha atomicupdate file for a bug. Arguments: bug number (e.g. 12345) and a short description of the DB change.
---

Create an atomicupdate file for Koha bug $ARGUMENTS.

Steps:
1. Parse arguments: first token is the bug number, remainder is the description.
2. Create the file `installer/data/mysql/atomicupdate/bug_BUGNUMBER.pl` using the skeleton below.
3. Replace `BUG_NUMBER` with the actual bug number and `DESCRIPTION` with the description.
4. Leave the `$dbh->do(q{})` placeholder in place — the user will fill in the actual SQL.
5. Make the file executable: `chmod +x installer/data/mysql/atomicupdate/bug_BUGNUMBER.pl` (Koha QA's `file_permissions` check enforces this).
6. Report the created file path.

Skeleton (based on `installer/data/mysql/atomicupdate/skeleton.pl`):
```perl
use Modern::Perl;
use Koha::Installer::Output qw(say_warning say_success say_info);

return {
    bug_number  => "BUG_NUMBER",
    description => "DESCRIPTION",
    up          => sub {
        my ($args) = @_;
        my ( $dbh, $out ) = @$args{qw(dbh out)};

        # Add your DB changes here
        $dbh->do(q{});

        say_success( $out, "Done" );
    },
};
```

After the user fills in the SQL, remind them of the wider workflow:
1. Update `installer/data/mysql/kohastructure.sql` to match.
2. Apply inside KTD: `perl installer/data/mysql/updatedatabase.pl`.
3. Regenerate DBIC schema: `dbic --force` inside KTD.
4. For new `tinyint(1)` columns that semantically represent yes/no flags, add `'+colname' => { is_boolean => 1 }` to the Result module BELOW the `# DO NOT MODIFY THIS OR ANYTHING ABOVE!` line (QA SQL12 / `tinyint_has_boolean_flag`).
5. Commit auto-generated DBIC changes as `Bug XXXXX: Automated Schema Update`, then commit any manual `is_boolean` / relationship additions as a separate commit.
