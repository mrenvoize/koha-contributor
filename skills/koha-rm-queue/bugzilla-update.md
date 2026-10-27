# Bugzilla batch update helper (Gate 3 of koha-rm-queue)

A short Perl snippet Claude writes to its **scratch directory** and runs —
never committed, never saved into a repo. It drives
`GitBz::Commands->new->{client}` (the `GitBz::RestClient` from `perl-git-bz`),
which logs in from the maintainer's existing `git bz` configuration
(`bz-tracker.<host>.*` in git config / the git credential helper), so the
script itself needs **no credential, must never read one from config, and
must never print one**. It works for restricted/security bugs, where raw
`curl` writes must never be used.

Run it from inside a git checkout under the Koha tree (`GitBz::Config`
shells out to `git config`, so it must run in a repo where the
`bz-tracker` config resolves) — the core `main` worktree is right.

## Locating the perl-git-bz lib

Never hard-code an absolute home path. Resolve it:

```bash
perl -MGitBz::Commands -e1 2>/dev/null && echo installed
```

If that fails, derive the lib directory from the `git-bz` executable
(`GITBZ_LIB=$(dirname "$(readlink -f "$(command -v git-bz)")")/../lib`) or,
if that does not resolve, ask the maintainer once where their `perl-git-bz`
checkout lives, and pass it with `perl -I"$GITBZ_LIB" ...`.

## The snippet

Fill in: `$comment` with the **approved** draft (verbatim, blank lines
intact), `$version` with the release-version string, and the two bug lists.
Write it to the scratch directory (e.g. `<scratchpad>/bz_pushed.pl`) and run
`perl -I"$GITBZ_LIB" <scratchpad>/bz_pushed.pl`.

```perl
use strict;
use warnings;
use GitBz::Commands;

my $client  = GitBz::Commands->new->{client};
my $comment = <<'TEXT';
<the approved comment, exactly as shown to the maintainer>
TEXT
chomp $comment;
my $version = '<e.g. 26.11.00>';

# Bugs pushed this batch: comment + status + release version.
my @pushed = qw(NNNNN NNNNN);
# Bugs only commented on (e.g. an RM follow-up explained): comment only.
my @comment_only = qw();

for my $id (@pushed) {
    my $bug     = $client->get_bug($id);
    my $cur_ver = $bug->{cf_release_version} // '';
    my $already = grep { ( $_->{text} // '' ) eq $comment }
        @{ $client->get_comments($id) };

    my %params;
    $params{comment} = { body => $comment } unless $already;
    unless ( grep { $_ eq $version } split /\s*,\s*/, $cur_ver ) {
        $params{cf_release_version} =
            length $cur_ver ? "$cur_ver, $version" : $version;
    }
    if ( $bug->{status} eq 'Passed QA' ) {
        $params{status} = 'Pushed to main';
    }
    elsif ( $bug->{status} ne 'Pushed to main' ) {
        print "$id: SKIPPED status change, status is '$bug->{status}' (expected Passed QA)\n";
    }
    if ( !%params ) { print "$id: nothing to do\n"; next }
    $client->update_bug( $id, %params );
    print "$id: updated (" . join( ' ', sort keys %params ) . ")\n";
}

for my $id (@comment_only) {
    $client->update_bug( $id, comment => { body => $comment } );
    print "$id: commented\n";
}

# Read-back: verify every bug, report mismatches.
print "--- verify\n";
for my $id ( @pushed, @comment_only ) {
    my $bug = $client->get_bug($id);
    my $n   = grep { ( $_->{text} // '' ) eq $comment }
        @{ $client->get_comments($id) };
    printf "%s | %s | released in: '%s' | matching comments: %d\n",
        $id, $bug->{status}, $bug->{cf_release_version} // '', $n;
}
```

## Field names and calls (confirmed against perl-git-bz and Koha's Bugzilla)

| What | Call / field |
|------|--------------|
| Read a bug (status, release version, deps) | `$client->get_bug($id)` — returns `status`, `cf_release_version`, `depends_on`, ... |
| Read comments | `$client->get_comments($id)` — arrayref of `{text, creator, creation_time, ...}` |
| Post a comment | `$client->update_bug($id, comment => { body => $text })` |
| Set status | `$client->update_bug($id, status => 'Pushed to main')` — valid only from `Passed QA` |
| "Version(s) released in" | `$client->update_bug($id, cf_release_version => '<existing>, <version>')` — a comma-separated string; append, never overwrite |
| Dependencies | `$client->update_bug($id, depends_on => { add => [N], remove => [N] })` |

Several updates can go in one `update_bug` call (status + comment +
`cf_release_version` together), as above.

## Rules

- The comment body goes in **verbatim** from the approved draft — the client
  posts it as-is (unlike `git bz edit --comment`, whose older builds strip
  blank lines and `#`-prefixed lines).
- Idempotent: re-running must not duplicate the comment, re-append the
  version, or fight an already-correct status — the checks above do that.
- A mismatch on read-back (wrong status, missing version, 0 or 2 matching
  comments) is reported to the maintainer, never retried in a loop.
- The expected output per bug is one `updated (...)` line and one verify
  line; anything else (a thrown `GitBz::Exception`, an HTTP error) is shown
  to the maintainer as-is — minus any credential, should one ever appear in
  an error string.
