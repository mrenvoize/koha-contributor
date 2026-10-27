# Bugzilla batch update helper (Gate 3 of koha-rm-queue)

A short Perl snippet you write to your **scratch directory** and run — never
committed, never saved into a repo. It drives
`GitBz::Commands->new->{client}` (the `GitBz::RestClient` from `perl-git-bz`),
which logs in from the maintainer's existing `git bz` configuration
(`bz-tracker.<host>.*` in git config / the git credential helper), so the
script itself needs **no credential, must never read one from config, and
must never print one**. It works for restricted/security bugs, where raw
`curl` writes must never be used.

Run it from inside a git checkout under the Koha tree (`GitBz::Config`
shells out to `git config`, so it must run in a repo where the
`bz-tracker` config resolves) — the core `main` worktree is right.

**DEBUG must never be set**: the client's debug mode prints the login
response (which contains the Bugzilla session token) and, for attachments,
the token itself. The snippet scrubs it in a `BEGIN` block, and you run it
with the variable removed as well:

```bash
env -u DEBUG perl ${GITBZ_LIB:+-I"$GITBZ_LIB"} <scratchpad>/bz_pushed.pl --preview
```

## Locating the perl-git-bz lib

Never hard-code an absolute home path. Resolve it:

```bash
perl -MGitBz::Commands -e1 2>/dev/null && echo installed
```

If that fails, derive it from the `git-bz` executable and **check it
exists** before use:

```bash
GITBZ_LIB=$(dirname "$(readlink -f "$(command -v git-bz)")")/../lib
[ -d "$GITBZ_LIB/GitBz" ] || echo "not found - ask the maintainer where perl-git-bz lives"
```

If neither resolves, ask the maintainer once for their `perl-git-bz`
checkout and use `<checkout>/lib`.

## The snippet

Fill in: `$comment` with the **approved** draft (verbatim, blank lines
intact), `$version` with the release-version string, and the two bug lists.
Run it first with `--preview` (reads only, prints the planned changes and
the `released in: '<old>' -> '<new>'` transitions for the Gate 3 approval),
then, after the maintainer approves, without it.

```perl
BEGIN { delete $ENV{DEBUG} }    # GitBz debug mode leaks the session token
use strict;
use warnings;
use JSON qw(decode_json);
use GitBz::Commands;

my $preview = grep { $_ eq '--preview' } @ARGV;
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

# get_bug() hard-codes its include_fields and leaves out cf_release_version,
# so read it with an explicit GET on the client's authenticated session.
# Never print the URL: it carries the session token.
sub read_bug {
    my ($id) = @_;
    my $url = sprintf '%s/bug/%s?include_fields=id,status,cf_release_version',
        $client->{base_url}, $id;
    my $token = $client->get_token;
    $url .= "&token=$token" if $token;
    my $resp = $client->{ua}->get($url);
    return undef unless $resp->is_success;
    my $data = eval { decode_json( $resp->content ) } or return undef;
    return $data->{bugs}[0];
}

# Normalise a comment body for comparison (line endings, trailing space).
sub norm {
    my $t = shift // '';
    $t =~ s/\r//g;
    $t =~ s/[ \t]+$//mg;
    $t =~ s/\s+\z//;
    return $t;
}

sub has_comment {
    my ($id) = @_;
    return scalar grep { norm( $_->{text} // $_->{body} ) eq norm($comment) }
        @{ $client->get_comments($id) };
}

for my $id (@pushed) {
    my $ok = eval {
        my $bug = read_bug($id) or die "could not read bug (fail closed)\n";
        my $cur_ver = $bug->{cf_release_version};
        my %params;
        $params{comment} = { body => $comment } unless has_comment($id);
        if ( defined $cur_ver ) {
            my %have = map { $_ => 1 } grep { length } split /[,\s]+/, $cur_ver;
            if ( !$have{$version} ) {
                $params{cf_release_version} =
                    length $cur_ver ? "$cur_ver, $version" : $version;
            }
        }
        else {
            print "$id: REFUSING version write: could not read current value\n";
        }
        if    ( $bug->{status} eq 'Passed QA' ) { $params{status} = 'Pushed to main' }
        elsif ( $bug->{status} ne 'Pushed to main' ) {
            print "$id: SKIPPED status change, status is '$bug->{status}' (expected Passed QA)\n";
        }
        if ( !%params ) { print "$id: nothing to do\n"; return 1 }
        if ($preview) {
            printf "%s: WOULD set %s | released in: '%s' -> '%s'\n", $id,
                join( ' ', sort keys %params ), $cur_ver // '(unreadable)',
                $params{cf_release_version} // ( $cur_ver // '(unchanged)' );
            return 1;
        }
        $client->update_bug( $id, %params );
        print "$id: updated (" . join( ' ', sort keys %params ) . ")\n";
        return 1;
    };
    print "$id: ERROR $@" unless $ok;
}

for my $id (@comment_only) {
    my $ok = eval {
        if ( has_comment($id) ) { print "$id: comment already present\n"; return 1 }
        if ($preview)           { print "$id: WOULD comment\n";           return 1 }
        $client->update_bug( $id, comment => { body => $comment } );
        print "$id: commented\n";
        return 1;
    };
    print "$id: ERROR $@" unless $ok;
}

# Read-back: verify every bug, report mismatches (runs even after errors).
print $preview ? "--- preview only, nothing written\n" : "--- verify\n";
for my $id ( @pushed, @comment_only ) {
    my $ok = eval {
        my $bug = read_bug($id) or die "could not read bug\n";
        printf "%s | %s | released in: '%s' | matching comments: %d\n",
            $id, $bug->{status}, $bug->{cf_release_version} // '(unreadable)',
            has_comment($id);
        return 1;
    };
    print "$id: VERIFY ERROR $@" unless $ok;
}
```

## Field names and calls

Confirmed against `perl-git-bz` (`lib/GitBz/RestClient.pm`) and Koha's live
Bugzilla, **except the noted `get_bug` gap**:

| What | Call / field |
|------|--------------|
| Read status + release version | `read_bug($id)` above — an explicit GET with `include_fields=id,status,cf_release_version` on the client's session |
| Read comments | `$client->get_comments($id)` — arrayref of `{text, creator, creation_time, ...}`; entries carry `text` (the client POD says `body`, the helper handles both) |
| Post a comment | `$client->update_bug($id, comment => { body => $text })` |
| Set status | `$client->update_bug($id, status => 'Pushed to main')` — valid only from `Passed QA` |
| "Version(s) released in" | `$client->update_bug($id, cf_release_version => '<current>, <version>')` — a comma-separated string; write it only after reading the current value, appending |
| Dependencies | `$client->update_bug($id, depends_on => { add => [N], remove => [N] })` |

Several updates can go in one `update_bug` call (status + comment +
`cf_release_version` together), as above.

**Known client gap**: `GitBz::RestClient::get_bug` hard-codes its
`include_fields` list and omits `cf_release_version`, so `get_bug` alone
would return it as undef and a naive append would **overwrite** the field.
That is why `read_bug` above exists and why the version is written only when
the current value was successfully read and defined. A one-word upstream fix
(adding `cf_release_version` to `get_bug`'s include_fields) would make this
simpler — do not patch the local `perl-git-bz` checkout from this skill.

## Rules

- Never run with `DEBUG` set (the `BEGIN` block plus `env -u DEBUG`); never
  print client debug output or the request URLs (they carry the session
  token).
- The comment body goes in **verbatim** from the approved draft — the client
  posts it as-is (unlike `git bz edit --comment`, whose older builds strip
  blank lines and `#`-prefixed lines).
- Preview first: `--preview` performs only reads and prints the planned
  comment/status/version changes; show its output at Gate 3 before any
  write.
- Idempotent on every posting path: re-running must not duplicate a comment
  (the normalised `has_comment` check guards both loops), re-append the
  version, or fight an already-correct status.
- The version field is **never written blind**: no successful read of the
  current value (undef / missing / HTTP error) means that bug's version
  write is refused and reported.
- A mismatch on read-back (wrong status, missing version, 0 or 2 matching
  comments) is reported to the maintainer, never retried in a loop.
- Each bug is wrapped in `eval`; one failure prints `<id>: ERROR ...` and
  the rest of the batch and the verify loop still run. Errors are shown
  as-is — minus any credential, should one ever appear in an error string.
